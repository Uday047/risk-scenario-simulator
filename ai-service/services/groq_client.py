"""
groq_client.py — Groq LLM client with retry logic and Redis caching.
Day 13 optimisation: cache responses by prompt SHA-256 to cut repeat latency.
"""
import os
import time
import logging
from groq import Groq
from dotenv import load_dotenv
from services.cache_client import cache_get, cache_set

load_dotenv()

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_groq(prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str | None:
    """
    Call the Groq LLaMA model with retry logic and optional Redis caching.

    Cache behaviour:
    - Only deterministic calls (temperature <= 0.3) are cached.
    - Cache miss → call Groq → store result → return.
    - Cache hit → return immediately (no Groq call).
    - If Redis is down the function works as if caching is disabled.
    """
    use_cache = temperature <= 0.3

    # ── Cache read ─────────────────────────────────────────────────────────
    if use_cache:
        cached = cache_get(prompt)
        if cached is not None:
            logger.info("Cache hit — skipping Groq call")
            return cached

    # ── Groq call with exponential-backoff retry ───────────────────────────
    retries = 3
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content

            # ── Cache write ────────────────────────────────────────────────
            if use_cache and result:
                cache_set(prompt, result)

            return result

        except Exception as e:
            logger.error(f"Groq call failed (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None