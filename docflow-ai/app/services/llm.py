"""
LLM Service — Ollama Integration
=================================
Sends extracted text to a local Ollama model (Qwen2.5, Mistral, LLaMA)
and parses structured invoice JSON from the response.
"""

import json
import re
from typing import Any, Optional

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


# ─── Extraction Prompt ───────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an expert invoice data extraction system.
Extract ALL available information from the invoice text below and return it as valid JSON.

INVOICE TEXT:
{text}

Return ONLY a JSON object with this exact structure (use null for missing fields):
{{
  "invoice_number": "string or null",
  "vendor_name": "string or null",
  "vendor_address": "string or null",
  "vendor_email": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "subtotal": number_or_null,
  "tax": number_or_null,
  "total_amount": number_or_null,
  "currency": "USD",
  "payment_terms": "string or null",
  "notes": "string or null",
  "line_items": [
    {{
      "description": "item description",
      "quantity": number_or_null,
      "unit_price": number_or_null,
      "total": number_or_null
    }}
  ]
}}

Rules:
- All monetary values must be numbers (not strings). Remove currency symbols.
- Dates must be YYYY-MM-DD format.
- line_items must be a list even if only one item.
- Return ONLY the JSON object, no explanation, no markdown fences.
"""

CONFIDENCE_PROMPT = """You are evaluating the quality of invoice data extraction.
Given the original text and extracted data, score each field's confidence (0.0 to 1.0).

ORIGINAL TEXT (first 1000 chars):
{text_snippet}

EXTRACTED DATA:
{extracted_json}

Return ONLY a JSON object with field names as keys and confidence scores (0.0-1.0) as values:
{{
  "invoice_number": 0.95,
  "vendor_name": 0.98,
  "invoice_date": 0.90,
  "total_amount": 0.87,
  "line_items": 0.75,
  "overall": 0.89
}}

Base scores on: field presence, data quality, format correctness, logical consistency.
Return ONLY the JSON object.
"""


class LLMService:
    """Interfaces with Ollama for invoice extraction and confidence scoring."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _generate(self, prompt: str) -> str:
        """Call Ollama /api/generate endpoint."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,   # low temp = deterministic extraction
                        "top_p": 0.9,
                        "num_predict": 2048,
                    }
                }
            )
            response.raise_for_status()
            return response.json()["response"]

    async def extract_invoice(self, raw_text: str) -> dict[str, Any]:
        """Extract structured invoice data from raw OCR text."""
        # Truncate very long texts to avoid context overflow
        text = raw_text[:4000] if len(raw_text) > 4000 else raw_text

        prompt = EXTRACTION_PROMPT.format(text=text)
        logger.info(f"Sending to Ollama ({self.model}): {len(text)} chars")

        raw_response = await self._generate(prompt)
        return self._parse_json_response(raw_response)

    async def score_confidence(
        self, raw_text: str, extracted_data: dict
    ) -> dict[str, float]:
        """Ask the LLM to self-score confidence of its own extraction."""
        prompt = CONFIDENCE_PROMPT.format(
            text_snippet=raw_text[:1000],
            extracted_json=json.dumps(extracted_data, indent=2)[:2000],
        )
        raw_response = await self._generate(prompt)
        scores = self._parse_json_response(raw_response)

        # Ensure all values are floats between 0 and 1
        return {
            k: max(0.0, min(1.0, float(v)))
            for k, v in scores.items()
            if isinstance(v, (int, float))
        }

    async def check_health(self) -> bool:
        """Verify Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                models = [m["name"] for m in r.json().get("models", [])]
                available = any(self.model.split(":")[0] in m for m in models)
                if not available:
                    logger.warning(
                        f"Model '{self.model}' not pulled yet. "
                        f"Run: docker exec docflow-ollama ollama pull {self.model}"
                    )
                return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def _parse_json_response(self, text: str) -> dict:
        """Robustly parse JSON from LLM output (handles fences, extra text)."""
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        text = text.replace("```", "").strip()

        # Find first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.warning(f"No JSON found in LLM response: {text[:200]}")
            return {}

        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e} | raw: {text[:300]}")
            return {}


llm_service = LLMService()
