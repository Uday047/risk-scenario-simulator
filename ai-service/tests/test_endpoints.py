"""
Day 10 — AI Developer 1
pytest unit tests for all AI service endpoints.
All Groq API calls are mocked — no real API calls made.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

# ── Patch heavy services before importing app ──────────────────────────────
import sys
import types

# Stub out chromadb + sentence_transformers so they don't need to be installed
# in the test runner (they are still in requirements.txt for production).
chroma_stub = types.ModuleType("chromadb")
chroma_stub.PersistentClient = MagicMock(return_value=MagicMock(
    get_or_create_collection=MagicMock(return_value=MagicMock())
))
sys.modules.setdefault("chromadb", chroma_stub)

st_stub = types.ModuleType("sentence_transformers")
st_stub.SentenceTransformer = MagicMock(return_value=MagicMock(
    encode=MagicMock(return_value=[0.1] * 384)
))
sys.modules.setdefault("sentence_transformers", st_stub)

from app import app  # noqa: E402  (import after stubs)


# ── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Shared mock payloads ───────────────────────────────────────────────────
DESCRIBE_MOCK = json.dumps({
    "title": "Data Breach Risk",
    "description": "Sensitive data may be exposed.",
    "impact": "High financial and reputational damage.",
    "likelihood": "High",
    "category": "Technical",
    "generated_at": "2026-05-04T00:00:00"
})

RECOMMEND_MOCK = json.dumps({
    "recommendations": [
        {"action_type": "Prevent", "description": "Encrypt all data at rest.", "priority": "High"},
        {"action_type": "Mitigate", "description": "Deploy intrusion detection.", "priority": "High"},
        {"action_type": "Transfer", "description": "Get cyber insurance.", "priority": "Medium"}
    ]
})

REPORT_MOCK = json.dumps({
    "title": "Q1 Risk Report",
    "executive_summary": "Three critical risks identified.",
    "overview": "Overview text here.",
    "top_items": [],
    "recommendations": []
})

ANALYSE_MOCK = json.dumps({
    "findings": [
        {
            "type": "Risk",
            "title": "Supply chain disruption",
            "description": "Key supplier may fail.",
            "severity": "High",
            "recommendation": "Diversify suppliers."
        }
    ],
    "summary": "One high-severity risk identified.",
    "total_findings": 1,
    "risk_count": 1,
    "insight_count": 0
})


# ══════════════════════════════════════════════════════════════════════════════
# Test 1 — GET /health
# ══════════════════════════════════════════════════════════════════════════════
def test_health(client):
    """Health endpoint returns 200 with expected keys."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "model" in data
    assert "service" in data


# ══════════════════════════════════════════════════════════════════════════════
# Test 2 — POST /describe — valid input
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.describe.call_groq", return_value=DESCRIBE_MOCK)
def test_describe_success(mock_groq, client):
    """Valid input returns structured JSON and 200."""
    res = client.post("/describe", json={"input": "A major ransomware attack on our servers"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Data Breach Risk"
    assert data["likelihood"] == "High"
    mock_groq.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# Test 3 — POST /describe — missing input field
# ══════════════════════════════════════════════════════════════════════════════
def test_describe_missing_input(client):
    """Missing input field returns 400."""
    res = client.post("/describe", json={})
    assert res.status_code == 400
    assert "error" in res.get_json()


# ══════════════════════════════════════════════════════════════════════════════
# Test 4 — POST /describe — input too short
# ══════════════════════════════════════════════════════════════════════════════
def test_describe_too_short(client):
    """Input shorter than 10 chars returns 400."""
    res = client.post("/describe", json={"input": "short"})
    assert res.status_code == 400
    assert res.get_json()["error"] == "input too short"


# ══════════════════════════════════════════════════════════════════════════════
# Test 5 — POST /recommend — valid input
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.recommend.call_groq", return_value=RECOMMEND_MOCK)
def test_recommend_success(mock_groq, client):
    """Valid input returns recommendations list and 200."""
    res = client.post("/recommend", json={"input": "Cloud infrastructure outage scenario"})
    assert res.status_code == 200
    data = res.get_json()
    assert "recommendations" in data
    assert len(data["recommendations"]) == 3
    mock_groq.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# Test 6 — POST /recommend — missing input field
# ══════════════════════════════════════════════════════════════════════════════
def test_recommend_missing_input(client):
    """Missing input field returns 400."""
    res = client.post("/recommend", json={"wrong_key": "something"})
    assert res.status_code == 400
    assert "error" in res.get_json()


# ══════════════════════════════════════════════════════════════════════════════
# Test 7 — POST /generate-report — valid input
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.generate_report.call_groq", return_value=REPORT_MOCK)
def test_generate_report_success(mock_groq, client):
    """Valid input returns report JSON and 200."""
    res = client.post("/generate-report", json={"input": "Q1 operational and financial risks for our SaaS platform"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Q1 Risk Report"
    assert "executive_summary" in data
    mock_groq.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# Test 8 — POST /generate-report — Groq failure → 503
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.generate_report.call_groq", return_value=None)
def test_generate_report_groq_failure(mock_groq, client):
    """When Groq returns None, endpoint returns 503 with is_fallback=True."""
    res = client.post("/generate-report", json={"input": "Q1 operational and financial risks for our SaaS platform"})
    assert res.status_code == 503
    data = res.get_json()
    assert data["is_fallback"] is True
    assert "error" in data


# ══════════════════════════════════════════════════════════════════════════════
# Test 9 — POST /analyse-document — valid input
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.analyse_document.call_groq", return_value=ANALYSE_MOCK)
def test_analyse_document_success(mock_groq, client):
    """Valid document text returns findings array and 200."""
    long_text = "Our main supplier recently announced financial difficulties. " * 5
    res = client.post("/analyse-document", json={"input": long_text})
    assert res.status_code == 200
    data = res.get_json()
    assert "findings" in data
    assert data["total_findings"] == 1
    assert data["risk_count"] == 1
    mock_groq.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# Test 10 — POST /query — valid question (RAG)
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.query.query_knowledge", return_value=["Relevant chunk about supply chain risk."])
@patch("routes.query.call_groq", return_value="Supply chain risks require diversified sourcing strategies.")
def test_query_success(mock_groq, mock_rag, client):
    """Valid question returns answer + sources and 200."""
    res = client.post("/query", json={"question": "What are supply chain risks?"})
    assert res.status_code == 200
    data = res.get_json()
    assert "answer" in data
    assert "sources" in data
    assert data["total_sources"] == 1
    mock_groq.assert_called_once()
    mock_rag.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# Test 11 — POST /batch-process — valid 2-item batch
# ══════════════════════════════════════════════════════════════════════════════
@patch("routes.batch_process.call_groq", return_value=DESCRIBE_MOCK)
def test_batch_process_success(mock_groq, client):
    """Valid batch of 2 describe items returns ordered results and 200."""
    payload = {
        "items": [
            {"type": "describe", "input": "A ransomware attack on our cloud infrastructure"},
            {"type": "describe", "input": "Supply chain disruption affecting key vendors"},
        ]
    }
    res = client.post("/batch-process", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["type"] == "describe"
    assert data["results"][0]["error"] is None
    assert mock_groq.call_count == 2


# ══════════════════════════════════════════════════════════════════════════════
# Test 12 — POST /batch-process — exceeds 20-item limit
# ══════════════════════════════════════════════════════════════════════════════
def test_batch_process_too_many_items(client):
    """Sending more than 20 items returns 400."""
    payload = {
        "items": [
            {"type": "describe", "input": "Risk scenario number " + str(i) * 5}
            for i in range(21)
        ]
    }
    res = client.post("/batch-process", json=payload)
    assert res.status_code == 400
    assert "Too many items" in res.get_json()["error"]
