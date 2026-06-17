<div align="center">

<img src="https://img.shields.io/badge/TruthLens-AI%20Reality%20Checker-7c3aed?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIj48Y2lyY2xlIGN4PSIxMSIgY3k9IjExIiByPSI4Ii8+PHBhdGggZD0ibTIxIDIxLTQuMy00LjMiLz48L3N2Zz4=" />

# TruthLens — AI-Powered Reality Checker

**Detect fake news in real time using ML + Deep Learning + live web fact-checking**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3+-f7931e?style=flat-square&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[**Live Demo**](#running-locally) • [**Features**](#features) • [**Architecture**](#architecture) • [**Setup**](#setup)

![TruthLens Dashboard Preview](https://img.shields.io/badge/Dashboard-Glassmorphic%20Dark%20UI-260087?style=for-the-badge)

</div>

---

## 🔍 What is TruthLens?

TruthLens is a full-stack AI-powered fake news detection system that goes beyond static ML models. It combines:

- **Two trained NLP classifiers** (TF-IDF Logistic Regression + 1D CNN)
- **Real-time web fact-checking** via DuckDuckGo, Bing, Wikipedia, and Google Fact Check API
- **A 4-layer verification engine** that overrides incorrect model predictions using live evidence
- **Gemini AI explanations** for every verdict

> Built with a stunning glassmorphic React dashboard, FastAPI backend, and SQLite history tracking.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **Dual AI Models** | Switch between Logistic Regression (TF-IDF) and a 1D CNN (PyTorch) |
| 🌐 **Live Web Verification** | Searches DuckDuckGo, Bing, Wikipedia for real-world corroboration |
| 🏛️ **Google Fact Check API** | Integrates authoritative fact-check ratings (when API key provided) |
| 🧠 **Gemini Explanations** | Generates professional fact-check reports using Google Gemini 1.5 Flash |
| 📊 **Confidence Scoring** | Displays FAKE/REAL probability bars with blended web+model confidence |
| 📬 **Email Reports** | Send verification reports to any inbox via Resend API |
| 📁 **Analysis History** | Persistent SQLite storage with searchable scan archive |
| ⚡ **Async Pipeline** | Non-blocking web scraping via ThreadPoolExecutor |
| 🎨 **Premium Dark UI** | Glassmorphic design with looping background video and micro-animations |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                 │
│  Dashboard │ Model Switcher │ Results │ History │ Email  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (localhost:8000)
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  POST /analyze                                           │
│  ├── Step 1: ML/CNN Inference (local models)             │
│  ├── Step 2: fetch_web_sources() [async, thread pool]    │
│  │   ├── Google Fact Check Tools API                     │
│  │   ├── DuckDuckGo Lite → HTML fallback                 │
│  │   ├── Bing Search fallback                            │
│  │   └── Wikipedia Named Entity lookup                   │
│  ├── Step 3: verify_with_web_sources() [score + override]│
│  ├── Step 4: generate_explanation() [Gemini / local]     │
│  └── Step 5: Save to SQLite                              │
│                                                          │
│  GET  /history   │  DELETE /history   │  GET /health     │
│  POST /send-report (Resend email API)                    │
└─────────────────────────────────────────────────────────┘
```

### Verification Scoring System

```
Source Type          Weight    Notes
─────────────────────────────────────────────────────────
Google Fact Check    ★★★★★   Textual rating decoded directly
Snopes/PolitiFact    ★★★★    Fact-check domains get 3.5× weight
Reuters/BBC/AP       ★★★     Reputable news corroboration 2.5×
Wikipedia            ★★      Entity grounding context 0.8×
Generic Web          ★       Minimal weight 0.4–0.8×

Override triggers when |fake_score - real_score| ≥ 1.5
Final confidence = web_conf(65%) + model_conf(35%)
```

---

## 🤖 ML Models

### Classical ML — TF-IDF + Logistic Regression
- Tokenizes text into word/char n-grams
- TF-IDF weights each term against corpus frequency
- Logistic Regression maps weights → FAKE/REAL probability
- **Accuracy: 90.86%** | **Latency: ~4ms**

### Deep Learning — 1D Convolutional Neural Network
- Embedding layer: token IDs → 50-dim vector space
- Conv1D filters (kernel=3) capture bigram/trigram context
- Global Adaptive Max Pooling extracts dominant phrase signals
- Fully Connected layer → softmax classification
- **Accuracy: 85.75%** | **Latency: ~15ms**

---

## 📁 Project Structure

```
trulens-ai-powered-reality-checker/
├── app.py                  # FastAPI backend (main entry point)
├── explanation_engine.py   # Verification engine + web scraping + Gemini
├── cnn_model.py            # PyTorch 1D CNN architecture
├── database.py             # SQLite persistence layer
├── train.py                # Train the Classical ML model
├── train_cnn.py            # Train the 1D CNN model
├── predict.py              # CLI prediction utility
├── requirements.txt        # Python dependencies
├── .gitignore
│
├── models/                 # Trained model files (gitignored)
│   ├── model.pkl           # TF-IDF + LogReg (scikit-learn)
│   ├── cnn_model.pth       # 1D CNN weights (PyTorch)
│   └── cnn_vocab.json      # Token vocabulary
│
├── data/                   # Training datasets (gitignored)
│
└── frontend/               # React + Vite dashboard
    ├── src/
    │   ├── App.jsx          # Main dashboard component
    │   ├── App.css          # Glassmorphic component styles
    │   └── index.css        # Global CSS variables + tokens
    ├── index.html
    └── package.json
```

---

## 🚀 Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- pip

### 1. Clone the Repository
```bash
git clone https://github.com/Mahesh-011-vk/trulens-ai-powered-reality-checker.git
cd trulens-ai-powered-reality-checker
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Add API keys for enhanced detection
export GEMINI_API_KEY="your_gemini_api_key"
export GOOGLE_FACTCHECK_API_KEY="your_google_factcheck_key"
```

### 3. Train the Models
```bash
# Train Classical ML model (TF-IDF + Logistic Regression)
python train.py

# Train Deep Learning model (1D CNN)
python train_cnn.py
```

### 4. Start the Backend
```bash
uvicorn app:app --reload --port 8000
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 🔑 Optional API Keys

| Key | Purpose | Get It |
|---|---|---|
| `GEMINI_API_KEY` | AI-generated explanations via Gemini 1.5 Flash | [Google AI Studio](https://aistudio.google.com/) |
| `GOOGLE_FACTCHECK_API_KEY` | Authoritative fact-check ratings | [Google Cloud Console](https://console.cloud.google.com/) |

> Without these keys, TruthLens still works — it uses local linguistic analysis and DuckDuckGo/Bing/Wikipedia scraping as fallbacks.

---

## 📡 API Reference

```http
POST /analyze
Content-Type: application/json

{
  "text": "News claim to verify...",
  "model_type": "ml"   // or "cnn"
}
```

```http
GET  /health          # System status + active sources
GET  /history         # Fetch analysis history (SQLite)
DELETE /history       # Clear all history
DELETE /history/{id}  # Delete single entry
POST /send-report     # Email report via Resend
```

---

## 🌐 Real-World Verification Pipeline

TruthLens does **not** blindly trust its ML models. Every prediction is cross-referenced against live web sources:

1. **Google Fact Check API** — Searches for existing fact-check verdicts on the claim
2. **DuckDuckGo** — Targeted queries across Reuters, AP, Snopes, BBC, NYT
3. **Bing** — Fallback search engine if DDG is blocked
4. **Wikipedia** — Named entity extraction for factual grounding

If the web evidence contradicts the model, the prediction is **overridden** with the real-world verdict.

---

## 🛠️ Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — High-performance async API
- [PyTorch](https://pytorch.org/) — 1D CNN deep learning model
- [scikit-learn](https://scikit-learn.org/) — TF-IDF + Logistic Regression
- [SQLite](https://sqlite.org/) — Lightweight persistent history storage
- [Google Generative AI](https://ai.google.dev/) — Gemini 1.5 Flash explanations

**Frontend**
- [React 18](https://react.dev/) + [Vite](https://vitejs.dev/)
- Vanilla CSS with glassmorphism design system
- Geist Sans + General Sans typography
- Looping background video with `requestAnimationFrame` fade

**Integrations**
- [Resend](https://resend.com/) — Transactional email reports
- [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api)
- DuckDuckGo Lite / Bing Search scraping
- Wikipedia REST API

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- Training data: [LIAR dataset](https://paperswithcode.com/dataset/liar) and [Fake News Dataset](https://www.kaggle.com/c/fake-news)
- Fact-check sources: Snopes, PolitiFact, FactCheck.org, Reuters Fact Check
- UI inspiration: Modern glassmorphic dashboards

---

<div align="center">

Built with ❤️ by [Mahesh S](https://github.com/Mahesh-011-vk)

⭐ **Star this repo if you find it useful!**

</div>
