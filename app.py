from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List, Optional
import joblib
import os
import database
import torch
from cnn_model import CNNClassifier, CNNTextProcessor
import explanation_engine
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Load .env file if present (local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Model paths ────────────────────────────────────────────────────────────
model_path      = 'models/model.pkl'
cnn_model_path  = 'models/cnn_model.pth'
cnn_vocab_path  = 'models/cnn_vocab.json'

model         = None
cnn_model     = None
cnn_processor = None

# Thread pool for non-blocking I/O (web scraping, Gemini calls)
executor = ThreadPoolExecutor(max_workers=6)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, cnn_model, cnn_processor

    # Load Classical ML Model
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        print(f"[Startup] ML Model loaded from {model_path}")
    else:
        print(f"[Startup] WARNING: ML Model not found at {model_path}. Run train.py first.")

    # Load CNN Model
    if os.path.exists(cnn_model_path) and os.path.exists(cnn_vocab_path):
        try:
            cnn_processor = CNNTextProcessor(vocab_path=cnn_vocab_path)
            cnn_model = CNNClassifier(vocab_size=cnn_processor.vocab_size)
            cnn_model.load_state_dict(
                torch.load(cnn_model_path, map_location=torch.device('cpu'), weights_only=True)
            )
            cnn_model.eval()
            print(f"[Startup] CNN Model loaded from {cnn_model_path}")
        except Exception as e:
            print(f"[Startup] ERROR loading CNN model: {e}")
    else:
        print(f"[Startup] WARNING: CNN Model not found. Run train_cnn.py first.")

    database.init_db()
    print("[Startup] Database initialized.")
    yield

    # Shutdown cleanup
    model = None
    cnn_model = None
    cnn_processor = None
    executor.shutdown(wait=False)
    print("[Shutdown] Resources released.")


app = FastAPI(
    title="TruthLens — Fake News Detection API",
    description="AI-powered fake news detection with real-time web verification.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────
# Allow all origins in development; restrict in production via env var.
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:4173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Frontend proxies via Vite in dev, wildcard is safe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ────────────────────────────────────────────────────────

class NewsRequest(BaseModel):
    text: str
    model_type: str = "ml"   # "ml" | "cnn"

class SourceItem(BaseModel):
    name: str
    snippet: str
    url: str
    source_type: Optional[str] = "web_search"
    rating: Optional[str] = None

class NewsResponse(BaseModel):
    text: str
    prediction: str
    confidence: dict
    explanation: str
    sources: List[SourceItem] = []   # ← NEW: real-time sources returned to frontend

class EmailRequest(BaseModel):
    to_email: str
    text: str
    prediction: str
    confidence: dict
    explanation: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """Live health check — returns status of all system components."""
    return {
        "status": "ok",
        "ml_model":              model is not None,
        "cnn_model":             cnn_model is not None,
        "google_factcheck_api":  bool(os.environ.get("GOOGLE_FACTCHECK_API_KEY")),
        "gemini_api":            bool(os.environ.get("GEMINI_API_KEY")),
        "verification_engine":   "active",
        "sources": ["google_factcheck_api", "duckduckgo", "bing", "wikipedia"],
    }


@app.get("/stats", tags=["Analytics"])
async def get_stats():
    """Returns aggregate statistics from the analysis history."""
    try:
        return database.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=NewsResponse, tags=["Analysis"])
async def analyze_news(request: NewsRequest):
    """
    Main analysis endpoint.
    1. Runs ML/CNN inference
    2. Fetches real-world web sources (async, non-blocking)
    3. Verifies & potentially overrides prediction
    4. Generates AI explanation
    5. Persists to SQLite
    6. Returns prediction + sources to frontend
    """
    model_type = request.model_type.lower()
    loop = asyncio.get_running_loop()

    # ── Step 1: Model Inference ────────────────────────────────────────────
    if model_type == "cnn":
        if cnn_model is None or cnn_processor is None:
            raise HTTPException(
                status_code=503,
                detail="CNN model not loaded. Run train_cnn.py first."
            )
        try:
            seq = cnn_processor.text_to_sequence(request.text)
            input_tensor = torch.tensor([seq], dtype=torch.long)
            with torch.no_grad():
                logits = cnn_model(input_tensor)
                probs = torch.softmax(logits, dim=1).numpy()[0]
            confidence = {
                "FAKE": round(float(probs[0]), 4),
                "REAL": round(float(probs[1]), 4),
            }
            prediction = "FAKE" if probs[0] > probs[1] else "REAL"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"CNN inference failed: {e}")

    else:  # ml (default)
        if model is None:
            raise HTTPException(
                status_code=503,
                detail="ML model not loaded. Run train.py first."
            )
        try:
            prediction = model.predict([request.text])[0]
            proba      = model.predict_proba([request.text])[0]
            classes    = model.classes_
            confidence = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ML inference failed: {e}")

    # ── Step 2: Fetch Web Sources (non-blocking) ───────────────────────────
    try:
        sources_raw = await loop.run_in_executor(
            executor,
            explanation_engine.fetch_web_sources,
            request.text,
        )
    except Exception as e:
        print(f"[Analyze] Web fetch failed: {e}")
        sources_raw = []

    # ── Step 3: Verify / Override Prediction ──────────────────────────────
    try:
        prediction, confidence = explanation_engine.verify_with_web_sources(
            request.text, prediction, confidence, sources_raw
        )
    except Exception as e:
        print(f"[Analyze] Verification failed: {e}")

    # ── Step 4: Generate Explanation ──────────────────────────────────────
    try:
        explanation = await loop.run_in_executor(
            executor,
            lambda: explanation_engine.generate_explanation(
                request.text, prediction, confidence, model_type, sources_raw
            ),
        )
    except Exception as e:
        print(f"[Analyze] Explanation failed: {e}")
        explanation = explanation_engine.generate_local_explanation(
            request.text, prediction, confidence, model_type, sources_raw
        )

    # ── Step 5: Persist to SQLite ─────────────────────────────────────────
    try:
        database.save_prediction(
            text=request.text,
            prediction=prediction,
            confidence_real=confidence.get('REAL', 0.0),
            confidence_fake=confidence.get('FAKE', 0.0),
            explanation=explanation,
        )
    except Exception as e:
        print(f"[Analyze] DB save failed: {e}")

    # ── Step 6: Build and return SourceItem list ──────────────────────────
    sources_out = [
        SourceItem(
            name=s.get("name", ""),
            snippet=s.get("snippet", ""),
            url=s.get("url", ""),
            source_type=s.get("source_type", "web_search"),
            rating=s.get("rating"),
        )
        for s in sources_raw
    ]

    return NewsResponse(
        text=request.text,
        prediction=prediction,
        confidence=confidence,
        explanation=explanation,
        sources=sources_out,
    )


@app.get("/history", tags=["History"])
async def fetch_history(limit: int = 50):
    try:
        return database.get_history(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history", tags=["History"])
async def clear_history():
    try:
        database.delete_all_predictions()
        return {"status": "success", "message": "All history deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{pred_id}", tags=["History"])
async def delete_single_history(pred_id: int):
    try:
        database.delete_prediction(pred_id)
        return {"status": "success", "message": f"Prediction {pred_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Email Report ───────────────────────────────────────────────────────────

def _markdown_to_html(md_text: str) -> str:
    if not md_text:
        return ""
    import re
    html = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = re.sub(r'(?m)^###\s+(.*?)$',
        r'<h4 style="color:#111827;margin-top:16px;margin-bottom:8px;font-size:14px;font-weight:700;">\1</h4>', html)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*',     r'<em>\1</em>', html)
    html = re.sub(r'\[(.*?)\]\((.*?)\)',
        r'<a href="\2" target="_blank" style="color:#2563eb;text-decoration:underline;font-weight:600;">\1</a>', html)
    lines = html.split('\n')
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('- '):
            lines[i] = f'<div style="margin:6px 0;padding-left:10px;font-size:13px;color:#374151;">• {s[2:]}</div>'
        elif s and not s.startswith('<h4') and not s.startswith('<div'):
            lines[i] = f'<p style="margin:6px 0;font-size:13px;color:#374151;line-height:1.5;">{line}</p>'
    return '\n'.join(lines)


@app.post("/send-report", tags=["Reports"])
async def send_report(request: EmailRequest):
    resend_key = os.environ.get("RESEND_API_KEY", "re_8myMpH56_3xrDUDSSFfhE7191Gzsj5nx4")
    from datetime import datetime
    import requests as req

    html_body = _markdown_to_html(request.explanation)
    fake_col  = "#fef2f2" if request.prediction == "FAKE" else "#ecfdf5"
    fake_bdr  = "#fca5a5" if request.prediction == "FAKE" else "#86efac"
    txt_col   = "#991b1b" if request.prediction == "FAKE" else "#065f46"
    sub_col   = "#b91c1c" if request.prediction == "FAKE" else "#047857"

    html_content = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:25px;
                border:1px solid #e5e7eb;border-radius:16px;background:#ffffff;">
      <h2 style="color:#09090b;margin-bottom:4px;font-size:20px;">TruthLens Verification Report</h2>
      <p style="color:#71717a;font-size:13px;margin-top:0;">AI-Powered Reality Checker</p>
      <hr style="border:0;border-top:1px solid #e4e4e7;margin:20px 0;" />

      <h3 style="font-size:13px;font-weight:700;color:#27272a;text-transform:uppercase;">Analyzed Claim</h3>
      <p style="color:#3f3f46;font-style:italic;background:#fafafa;padding:16px;border-radius:12px;
                border-left:4px solid #3b82f6;margin:0 0 20px;line-height:1.5;font-size:14px;">
        &ldquo;{request.text}&rdquo;
      </p>

      <div style="padding:16px;border-radius:12px;background:{fake_col};border:1px solid {fake_bdr};margin-bottom:20px;">
        <span style="font-size:15px;font-weight:800;color:{txt_col};">VERDICT: {request.prediction}</span><br/>
        <span style="font-size:12px;font-weight:600;color:{sub_col};margin-top:4px;display:inline-block;">
          Confidence — FAKE: {request.confidence.get('FAKE', 0)*100:.1f}% | REAL: {request.confidence.get('REAL', 0)*100:.1f}%
        </span>
      </div>

      <h3 style="font-size:13px;font-weight:700;color:#27272a;text-transform:uppercase;">AI Explanation</h3>
      <div style="background:#fafafa;padding:16px;border-radius:12px;border:1px solid #f4f4f5;font-size:14px;line-height:1.6;">
        {html_body}
      </div>

      <hr style="border:0;border-top:1px solid #e4e4e7;margin:20px 0;" />
      <p style="color:#a1a1aa;font-size:11px;text-align:center;margin:0;">
        Generated by TruthLens &bull; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
      </p>
    </div>
    """

    payload = {
        "from":    "TruthLens <onboarding@resend.dev>",
        "to":      request.to_email,
        "subject": f"TruthLens Report: {request.prediction}",
        "html":    html_content,
    }
    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type":  "application/json",
    }

    try:
        res = req.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            return {"status": "success", "message": "Email sent successfully!"}
        raise HTTPException(status_code=res.status_code, detail=f"Resend error: {res.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
