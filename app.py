from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import joblib
import os
import database
import torch
from cnn_model import CNNClassifier, CNNTextProcessor
import explanation_engine
from concurrent.futures import ThreadPoolExecutor
import asyncio

model_path = 'models/model.pkl'
model = None

cnn_model_path = 'models/cnn_model.pth'
cnn_vocab_path = 'models/cnn_vocab.json'
cnn_model = None
cnn_processor = None

# Thread pool for running blocking I/O (web scraping) without blocking the event loop
executor = ThreadPoolExecutor(max_workers=4)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, cnn_model, cnn_processor
    # Load Classical ML Model
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        print(f"ML Model loaded successfully from {model_path}.")
    else:
        print(f"Warning: ML Model not found at {model_path}. Please train the model first.")
    
    # Load CNN Model
    if os.path.exists(cnn_model_path) and os.path.exists(cnn_vocab_path):
        try:
            cnn_processor = CNNTextProcessor(vocab_path=cnn_vocab_path)
            cnn_model = CNNClassifier(vocab_size=cnn_processor.vocab_size)
            cnn_model.load_state_dict(torch.load(cnn_model_path, map_location=torch.device('cpu')))
            cnn_model.eval()
            print(f"CNN Model loaded successfully from {cnn_model_path}.")
        except Exception as e:
            print(f"Error loading CNN model: {e}")
    else:
        print(f"Warning: CNN Model files not found. Please train the CNN model first.")
    
    # Initialize the prediction history database
    database.init_db()
    
    yield
    # Clean up at shutdown if necessary
    model = None
    cnn_model = None
    cnn_processor = None
    executor.shutdown(wait=False)

app = FastAPI(title="Fake News Detection API", lifespan=lifespan)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NewsRequest(BaseModel):
    text: str
    model_type: str = "ml"  # "ml" or "cnn"

class NewsResponse(BaseModel):
    text: str
    prediction: str
    confidence: dict
    explanation: str

@app.post("/analyze", response_model=NewsResponse)
async def analyze_news(request: NewsRequest):
    model_type = request.model_type.lower()
    
    # ── Step 1: Run model inference (fast, in-process) ────────────────────
    if model_type == "cnn":
        if cnn_model is None or cnn_processor is None:
            raise HTTPException(status_code=503, detail="CNN Model is not loaded. Please train the CNN model first.")
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

    else:  # Default to ML
        if model is None:
            raise HTTPException(status_code=503, detail="ML Model is not loaded. Please train the ML model first.")
        try:
            prediction = model.predict([request.text])[0]
            proba = model.predict_proba([request.text])[0]
            classes = model.classes_
            confidence = {cls: round(float(prob), 4) for cls, prob in zip(classes, proba)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ML inference failed: {e}")

    # ── Step 2: Fetch real-world sources concurrently (non-blocking) ──────
    try:
        loop = asyncio.get_event_loop()
        sources = await loop.run_in_executor(
            executor,
            explanation_engine.fetch_web_sources,
            request.text,
        )
    except Exception as e:
        print(f"[Analyze] Web source fetching failed: {e}")
        sources = []

    # ── Step 3: Verify + potentially override prediction ──────────────────
    try:
        prediction, confidence = explanation_engine.verify_with_web_sources(
            request.text, prediction, confidence, sources
        )
    except Exception as e:
        print(f"[Analyze] Verification failed: {e}")

    # ── Step 4: Generate AI explanation (Gemini or local fallback) ────────
    try:
        explanation = await loop.run_in_executor(
            executor,
            lambda: explanation_engine.generate_explanation(
                request.text, prediction, confidence, model_type, sources
            ),
        )
    except Exception as e:
        print(f"[Analyze] Explanation generation failed: {e}")
        explanation = explanation_engine.generate_local_explanation(
            request.text, prediction, confidence, model_type, sources
        )

    # ── Step 5: Persist to database ────────────────────────────────────────
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

    return NewsResponse(
        text=request.text,
        prediction=prediction,
        confidence=confidence,
        explanation=explanation,
    )


@app.get("/history")
async def fetch_history(limit: int = 50):
    try:
        return database.get_history(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history")
async def clear_history():
    try:
        database.delete_all_predictions()
        return {"status": "success", "message": "All history deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{pred_id}")
async def delete_single_history(pred_id: int):
    try:
        database.delete_prediction(pred_id)
        return {"status": "success", "message": f"Prediction {pred_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Returns the health status of all system components."""
    google_fc_key = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    return {
        "status": "ok",
        "ml_model": model is not None,
        "cnn_model": cnn_model is not None,
        "google_factcheck_api": bool(google_fc_key),
        "gemini_api": bool(gemini_key),
        "verification_engine": "active",
        "sources": ["google_factcheck_api", "duckduckgo", "bing", "wikipedia"],
    }


class EmailRequest(BaseModel):
    to_email: str
    text: str
    prediction: str
    confidence: dict
    explanation: str


def markdown_to_html(md_text: str) -> str:
    if not md_text:
        return ""
    import re
    html = md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = re.sub(r'(?m)^###\s+(.*?)$', r'<h4 style="color: #111827; margin-top: 16px; margin-bottom: 8px; font-size: 14px; font-weight: 700;">\1</h4>', html)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: 600;">\1</a>', html)
    lines = html.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('- '):
            lines[i] = f'<div style="margin: 6px 0; padding-left: 10px; font-size: 13px; color: #374151;">• {stripped[2:]}</div>'
        elif stripped and not stripped.startswith('<h4') and not stripped.startswith('<div'):
            lines[i] = f'<p style="margin: 6px 0; font-size: 13px; color: #374151; line-height: 1.5;">{line}</p>'
    return '\n'.join(lines)


@app.post("/send-report")
async def send_report(request: EmailRequest):
    resend_key = "re_8myMpH56_3xrDUDSSFfhE7191Gzsj5nx4"
    url = "https://api.resend.com/emails"

    from datetime import datetime
    import requests as req

    formatted_explanation = markdown_to_html(request.explanation)

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #e5e7eb; border-radius: 16px; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
        <h2 style="color: #09090b; margin-bottom: 4px; font-size: 20px;">TruthLens Verification Report</h2>
        <p style="color: #71717a; font-size: 13px; margin-top: 0; font-weight: 500;">AI-Powered Reality Checker</p>
        <hr style="border: 0; border-top: 1px solid #e4e4e7; margin: 20px 0;" />
        
        <div style="margin-bottom: 20px;">
            <h3 style="color: #27272a; margin-bottom: 8px; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Analyzed Claim</h3>
            <p style="color: #3f3f46; font-style: italic; background-color: #fafafa; padding: 16px; border-radius: 12px; border: 1px solid #f4f4f5; border-left: 4px solid #3b82f6; margin: 0; line-height: 1.5; font-size: 14px;">
                "{request.text}"
            </p>
        </div>
        
        <div style="margin-bottom: 24px; padding: 16px; border-radius: 12px; background-color: {'#fef2f2' if request.prediction == 'FAKE' else '#ecfdf5'}; border: 1px solid {'#fca5a5' if request.prediction == 'FAKE' else '#86efac'};">
            <span style="font-size: 15px; font-weight: 800; color: {'#991b1b' if request.prediction == 'FAKE' else '#065f46'}; letter-spacing: 0.02em;">
                VERDICT: {request.prediction}
            </span>
            <br/>
            <span style="font-size: 12px; font-weight: 600; color: {'#b91c1c' if request.prediction == 'FAKE' else '#047857'}; margin-top: 4px; display: inline-block;">
                Confidence: FAKE: {request.confidence.get('FAKE', 0.0)*100:.1f}% | REAL: {request.confidence.get('REAL', 0.0)*100:.1f}%
            </span>
        </div>
        
        <div style="margin-bottom: 20px;">
            <h3 style="color: #27272a; margin-bottom: 8px; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">AI Analytical Explanation</h3>
            <div style="color: #27272a; font-size: 14px; line-height: 1.6; background-color: #fafafa; padding: 16px; border-radius: 12px; border: 1px solid #f4f4f5;">
                {formatted_explanation}
            </div>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #e4e4e7; margin: 20px 0;" />
        <p style="color: #a1a1aa; font-size: 11px; text-align: center; margin: 0; font-weight: 500;">
            Report generated by TruthLens Dashboard • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
    """

    payload = {
        "from": "TruthLens <onboarding@resend.dev>",
        "to": request.to_email,
        "subject": f"TruthLens Verification Report: {request.prediction}",
        "html": html_content,
    }

    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json",
    }

    try:
        res = req.post(url, json=payload, headers=headers)
        if res.status_code in (200, 201):
            return {"status": "success", "message": "Email sent successfully!"}
        else:
            raise HTTPException(status_code=res.status_code, detail=f"Resend error: {res.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
