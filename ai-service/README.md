# AI Service — Risk Scenario Simulator

> **Tool-07 | Capstone Project | Sprint: 14 April – 9 May 2026**
> AI Developer 1: Uday Vivekanand Hosur

The AI service is a Flask-based REST API that powers the Risk Scenario Simulator. It uses **Groq (LLaMA-3.3-70b-versatile)** for AI inference, **ChromaDB** for RAG (Retrieval-Augmented Generation), and **sentence-transformers** for embedding generation.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web framework | Flask 3.0.3 |
| AI model | LLaMA-3.3-70b-versatile via Groq API |
| Vector store | ChromaDB 0.5.0 (persistent, local) |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers |
| Caching | Redis (optional — graceful fallback if unavailable) |
| Rate limiting | flask-limiter (30 req/min default) |
| Testing | pytest 8.2.2 + pytest-mock |
| Container | Docker |

---

## Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com/) (free tier available)
- Docker (optional, for containerised run)
- Redis (optional, for response caching)

---

## Setup — Local

### 1. Clone and navigate

```bash
git clone https://github.com/Uday047/risk-scenario-simulator.git
cd risk-scenario-simulator/ai-service
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in `ai-service/`:

```env
GROQ_API_KEY=your_groq_api_key_here
REDIS_URL=redis://localhost:6379/0   # optional
```

### 5. Run the service

```bash
python app.py
```

The service starts on **http://localhost:5000**.

---

## Setup — Docker

### Build the image

```bash
docker build -t ai-service .
```

### Run the container

```bash
docker run -p 5000:5000 --env-file .env ai-service
```

> **Note:** The `.env` file is excluded from the Docker image via `.gitignore`. Always pass secrets via `--env-file` or environment variables.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ Yes | — | Your Groq API key for LLaMA inference |
| `REDIS_URL` | ❌ No | `redis://localhost:6379/0` | Redis connection URL for response caching. If Redis is unreachable, caching is silently skipped and the service continues normally. |

---

## API Endpoints

All endpoints accept and return `application/json`.

### `GET /health`

Health check.

**Response `200`:**
```json
{
  "status": "ok",
  "model": "llama-3.3-70b-versatile",
  "service": "Risk Scenario Simulator AI"
}
```

---

### `POST /describe`

Describe a risk scenario in structured format.

**Request body:**
```json
{ "input": "A ransomware attack on our payment systems" }
```

**Response `200`:**
```json
{
  "title": "Ransomware Attack on Payment Systems",
  "description": "...",
  "impact": "High financial and reputational damage.",
  "likelihood": "High",
  "category": "Technical",
  "generated_at": "2026-05-04T12:00:00"
}
```

**Error responses:** `400` (missing/short input), `503` (AI unavailable)

---

### `POST /recommend`

Get 3 actionable recommendations for a risk scenario.

**Request body:**
```json
{ "input": "Cloud infrastructure outage due to region failure" }
```

**Response `200`:**
```json
{
  "recommendations": [
    { "action_type": "Prevent", "description": "...", "priority": "High" },
    { "action_type": "Mitigate", "description": "...", "priority": "High" },
    { "action_type": "Transfer", "description": "...", "priority": "Medium" }
  ]
}
```

---

### `POST /generate-report`

Generate a full structured risk report.

**Request body:**
```json
{ "input": "Q1 operational and financial risks for our SaaS platform" }
```

**Response `200`:**
```json
{
  "title": "Q1 Risk Report",
  "executive_summary": "...",
  "overview": "...",
  "top_items": [...],
  "recommendations": [...]
}
```

---

### `POST /generate-report/stream`

Same as `/generate-report` but streams the response as **Server-Sent Events (SSE)**.

**Request body:** same as `/generate-report`

**Response:** `text/event-stream`
```
data: {"token": "Q1"}
data: {"token": " Risk"}
...
data: [DONE]
```

---

### `POST /query`

RAG-powered Q&A against the ChromaDB knowledge base.

**Request body:**
```json
{ "question": "What are the most common supply chain risks?" }
```

**Response `200`:**
```json
{
  "answer": "Supply chain risks include...",
  "sources": ["Relevant chunk 1", "Relevant chunk 2"],
  "total_sources": 2
}
```

---

### `POST /analyse-document`

Analyse a document text and extract structured risk findings.

**Request body:**
```json
{ "input": "<paste document text here, min 20 characters>" }
```

**Response `200`:**
```json
{
  "findings": [
    {
      "type": "Risk",
      "title": "Supply Chain Disruption",
      "description": "...",
      "severity": "High",
      "recommendation": "Diversify suppliers."
    }
  ],
  "summary": "One high-severity risk identified.",
  "total_findings": 1,
  "risk_count": 1,
  "insight_count": 0
}
```

---

### `POST /batch-process`

Process up to **20 risk scenarios** in a single request. A 100ms delay is applied between items to respect Groq rate limits. Results are returned in the same order as the input.

**Request body:**
```json
{
  "items": [
    { "type": "describe", "input": "A data breach exposing customer PII" },
    { "type": "recommend", "input": "Insider threat from a disgruntled employee" },
    { "type": "generate_report", "input": "Annual cyber risk assessment" },
    { "type": "analyse_document", "input": "<document text>" }
  ]
}
```

Valid `type` values: `describe` | `recommend` | `generate_report` | `analyse_document`

**Response `200`:**
```json
{
  "total": 2,
  "results": [
    {
      "type": "describe",
      "input": "A data breach...",
      "result": { "title": "...", "description": "...", ... },
      "error": null
    },
    {
      "type": "recommend",
      "input": "Insider threat...",
      "result": { "recommendations": [...] },
      "error": null
    }
  ]
}
```

**Error responses:** `400` (missing items, invalid type, > 20 items)

---

## Running Tests

Run all 10 unit tests (Groq API is fully mocked — no real API calls):

```bash
python -m pytest tests/test_endpoints.py -v
```

Expected output:
```
10 passed in ~2s
```

---

## Project Structure

```
ai-service/
├── app.py                  # Flask app entry point, blueprint registration
├── Dockerfile              # Docker build instructions
├── requirements.txt        # Python dependencies
├── .env                    # Secret env vars (not committed)
├── prompts/                # LLM prompt templates (.txt files)
│   ├── describe.txt
│   ├── recommend.txt
│   ├── generate_report.txt
│   ├── query.txt
│   └── analyse_document.txt
├── routes/                 # Flask Blueprint route handlers
│   ├── describe.py
│   ├── recommend.py
│   ├── generate_report.py
│   ├── generate_report_stream.py
│   ├── query.py
│   ├── analyse_document.py
│   └── batch_process.py
├── services/               # Shared service clients
│   ├── groq_client.py      # Groq LLM client (with retry + cache)
│   ├── chroma_client.py    # ChromaDB RAG client
│   └── cache_client.py     # Redis cache client (graceful fallback)
├── tests/
│   ├── __init__.py
│   └── test_endpoints.py   # 10 pytest unit tests
└── chroma_data/            # ChromaDB persistent storage (not committed)
```

---

## Notes

- All secrets must be in `.env` — never commit the `.env` file.
- `chroma_data/` and `__pycache__/` are excluded from git via `.gitignore`.
- The service runs on **port 5000** by default.
- Redis caching is **optional** — the service works fully without it.
- Rate limiting is set to **30 requests/minute** per IP.
