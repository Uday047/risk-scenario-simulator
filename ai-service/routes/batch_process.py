"""
Day 11 — AI Developer 1
POST /batch-process — process up to 20 risk scenarios in one call.
Each item specifies a type (describe | recommend | generate_report | analyse_document)
and an input string. A 100ms delay is applied between items to respect Groq rate limits.
Returns an ordered array of results matching the input array.
"""
import time
import json
from flask import Blueprint, request, jsonify
from services.groq_client import call_groq
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
batch_process_bp = Blueprint("batch_process", __name__)

# Map type → (prompt file, call_groq kwargs)
ENDPOINT_CONFIG = {
    "describe": {
        "prompt_file": "describe.txt",
        "temperature": 0.3,
        "max_tokens": 600,
    },
    "recommend": {
        "prompt_file": "recommend.txt",
        "temperature": 0.7,
        "max_tokens": 600,
    },
    "generate_report": {
        "prompt_file": "generate_report.txt",
        "temperature": 0.3,
        "max_tokens": 1500,
    },
    "analyse_document": {
        "prompt_file": "analyse_document.txt",
        "temperature": 0.3,
        "max_tokens": 1500,
    },
}

VALID_TYPES = set(ENDPOINT_CONFIG.keys())
MAX_ITEMS = 20
DELAY_SECONDS = 0.1  # 100ms between items


def _load_prompt(prompt_file: str) -> str:
    path = os.path.join(BASE_DIR, "prompts", prompt_file)
    with open(path, "r") as f:
        return f.read()


def _process_item(item_type: str, user_input: str) -> dict:
    """Call Groq for a single item and return a result dict."""
    config = ENDPOINT_CONFIG[item_type]
    prompt_template = _load_prompt(config["prompt_file"])

    # describe prompt also has {generated_at} — replace with empty for batch
    from datetime import datetime
    prompt = (
        prompt_template
        .replace("{input}", user_input)
        .replace("{generated_at}", datetime.utcnow().isoformat())
        .replace("{context}", "")      # query prompt — no RAG context in batch
        .replace("{question}", user_input)
    )

    raw = call_groq(
        prompt,
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    if raw is None:
        return {
            "type": item_type,
            "input": user_input,
            "result": None,
            "error": "AI service unavailable",
        }

    # Try to parse JSON; fall back to raw string
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw

    return {
        "type": item_type,
        "input": user_input,
        "result": parsed,
        "error": None,
    }


@batch_process_bp.route("/batch-process", methods=["POST"])
def batch_process():
    data = request.get_json()

    # ── Validate request body ──────────────────────────────────────────────
    if not data or "items" not in data:
        return jsonify({"error": "items field is required"}), 400

    items = data["items"]
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "items must be a non-empty array"}), 400

    if len(items) > MAX_ITEMS:
        return jsonify({
            "error": f"Too many items. Maximum allowed is {MAX_ITEMS}, received {len(items)}."
        }), 400

    # ── Validate each item ─────────────────────────────────────────────────
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            return jsonify({"error": f"Item at index {idx} must be an object"}), 400
        if "type" not in item or "input" not in item:
            return jsonify({
                "error": f"Item at index {idx} must have 'type' and 'input' fields"
            }), 400
        if item["type"] not in VALID_TYPES:
            return jsonify({
                "error": f"Item at index {idx} has invalid type '{item['type']}'. "
                         f"Valid types: {sorted(VALID_TYPES)}"
            }), 400
        if not isinstance(item["input"], str) or len(item["input"].strip()) < 10:
            return jsonify({
                "error": f"Item at index {idx}: 'input' must be a string with at least 10 characters"
            }), 400

    # ── Process items with 100ms delay between each ────────────────────────
    results = []
    for idx, item in enumerate(items):
        if idx > 0:
            time.sleep(DELAY_SECONDS)
        result = _process_item(item["type"], item["input"].strip())
        results.append(result)

    return jsonify({
        "total": len(results),
        "results": results,
    }), 200
