"""LLM Adapter supporting Ollama, OpenAI, and deterministic offline synthesis."""
import json
import requests
import re
from typing import Dict, Any, List, Optional
from src.config import settings

class LLMAdapter:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Attempts to generate a completion using local Ollama instance."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=1.5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
        except Exception:
            pass
        return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        """Attempts to generate completion using OpenAI if configured."""
        if not self.openai_key:
            return None
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            resp = client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass
        return None

    def _deterministic_synthesize(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        product_context: Dict[str, Any]
    ) -> str:
        """
        Deterministic, offline quality synthesizer.
        Extracts verifiable facts from retrieved chunks without hallucinating.
        """
        if not retrieved_chunks:
            return (
                "**Direct Answer:** INSUFFICIENT EVIDENCE. No approved specifications or documentation "
                f"matching this inquiry were found for product {product_context.get('name', 'N/A')} "
                f"({product_context.get('sku', 'N/A')}).\n\n"
                "**Applicable Specification:** None identified in approved active database records.\n\n"
                "**Missing Information:** Missing product specification document or inspection procedure.\n\n"
                "**Recommended Action:** Upload or approve the official specification document for this SKU."
            )

        # Analyze keywords in query
        query_words = set(re.findall(r'\w+', query.lower()))
        matched_sentences = []
        citations = []

        for chunk in retrieved_chunks:
            text = chunk["content"]
            sentences = re.split(r'(?<=[.!?\n])\s+', text)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                s_words = set(re.findall(r'\w+', s_clean.lower()))
                overlap = query_words.intersection(s_words)
                if len(overlap) >= 2 or any(w in s_words for w in ["tolerance", "spec", "limit", "dimension", "reach", "defect", "pass", "fail", "standard"]):
                    matched_sentences.append(s_clean)
            
            citations.append(
                f"[Doc: {chunk['document_id']} | Rev: {chunk['revision']} | Page {chunk['page_number']} - {chunk['section_title']}]"
            )

        citations_unique = list(dict.fromkeys(citations))

        if matched_sentences:
            evidence_body = "\n".join(f"- {s}" for s in matched_sentences[:6])
        else:
            evidence_body = f"- {retrieved_chunks[0]['content'][:300]}..."

        answer = (
            f"### Evaluation & Specification Review for {product_context.get('name', 'Product')} ({product_context.get('sku', '')})\n\n"
            f"**Direct Answer:**\n"
            f"Based on {len(retrieved_chunks)} approved document passage(s) retrieved from the official quality repository:\n\n"
            f"**Verified Evidence Extracted:**\n{evidence_body}\n\n"
            f"**Source Citations:**\n" + "\n".join(f"* {c}" for c in citations_unique) + "\n\n"
            f"**Limitations & Missing Information:**\n"
            f"Findings are strictly bounded by the active approved specifications above. Any physical sample variation or unrecorded defect requires laboratory verification.\n\n"
            f"**Recommended Action:**\n"
            f"Cross-reference sample measurements with the cited dimensional and visual limits before closing this case."
        )
        return answer

    def generate_response(
        self,
        prompt: str,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        product_context: Dict[str, Any]
    ) -> str:
        """Generates response using available provider or falls back safely to deterministic synthesis."""
        # 1. Try Ollama if available
        resp = self._call_ollama(prompt)
        if resp:
            return resp

        # 2. Try OpenAI if configured
        resp = self._call_openai(prompt)
        if resp:
            return resp

        # 3. Deterministic offline fallback
        return self._deterministic_synthesize(query, retrieved_chunks, product_context)

llm_adapter = LLMAdapter()
