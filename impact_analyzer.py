"""
impact_analyzer.py
-------------------
Semantic impact analysis for requirement changes.
"""

import os
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from embedding_singleton import get_embedding_model
from logger import get_logger
from config import Config

logger = get_logger("ImpactAnalyzer")

# Module keyword heuristics (same set as qa_planner.py for consistency)
_MODULE_KEYWORDS = {
    "Authentication":   ["login", "logout", "auth", "password", "jwt", "token", "session", "oauth", "2fa", "register"],
    "Product Catalog":  ["product", "catalog", "category", "sku", "listing", "inventory"],
    "Shopping Cart":    ["cart", "basket", "add to cart", "wishlist", "quantity"],
    "Checkout":         ["checkout", "shipping", "delivery", "coupon", "promo code"],
    "Payment":          ["payment", "pay", "credit card", "stripe", "razorpay", "refund", "transaction"],
    "Order Management": ["order", "order history", "track order", "cancel order", "invoice"],
    "Admin Dashboard":  ["admin", "dashboard", "manage", "report", "analytics", "permission"],
    "API Layer":        ["api", "endpoint", "rest", "graphql", "rate limit", "webhook"],
    "UI/Frontend":      ["ui", "button", "form", "screen", "page", "interface"],
    "Database":         ["data", "store", "database", "sql", "query", "record"],
}


class ImpactAnalyzer:
    """
    Compares updated requirements against previously analyzed PRD content
    using semantic similarity to detect impacted modules and test cases.
    """

    def __init__(self):
        self.model_name = Config.EMBEDDING_MODEL
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model for ImpactAnalyzer: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load ImpactAnalyzer embedding model: {e}")
            self.model = None

        self.similarity_threshold = 0.75  # Tune to adjust sensitivity

    def analyze_impact(
        self,
        new_requirement: str,
        old_sentences: List[str],
        existing_test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyzes the impact of a new / changed requirement against the existing
        PRD sentences and generated test cases.

        Args:
            new_requirement: The new or changed requirement text.
            old_sentences:   PRD chunk sentences from session state.
            existing_test_cases: Generated test cases from session state.

        Returns:
            dict with keys: impacted_modules, impacted_test_cases,
                            impacted_prd_context, total_impacted_tcs
        """
        if not self.model:
            logger.error("Embedding model not loaded. Cannot analyze impact.")
            return {"impacted_modules": [], "impacted_test_cases": [], "total_impacted_tcs": 0}

        if not new_requirement or not old_sentences:
            return {"impacted_modules": [], "impacted_test_cases": [], "total_impacted_tcs": 0}

        try:
            # 1. Embed new requirement
            new_req_emb = self.model.encode([new_requirement])

            # 2. Find similar PRD sentences
            old_embs = self.model.encode(old_sentences)
            similarities = cosine_similarity(new_req_emb, old_embs)[0]

            impacted_sentences = []
            for i, sim in enumerate(similarities):
                if sim >= self.similarity_threshold:
                    impacted_sentences.append({
                        "sentence": old_sentences[i],
                        "similarity_score": round(float(sim), 3),
                    })

            # 3. Find impacted test cases
            # Build TC text using the same field names produced by agents.py
            impacted_tcs = []
            if existing_test_cases:
                tc_texts = []
                for tc in existing_test_cases:
                    # Field names used by agents.py output
                    scenario = tc.get("scenario", tc.get("title", ""))
                    # Steps field: agents produce 'steps' as list-of-dicts
                    steps_raw = tc.get("steps", tc.get("test_steps", []))
                    if isinstance(steps_raw, list):
                        step_parts = []
                        for s in steps_raw:
                            if isinstance(s, dict):
                                step_parts.append(s.get("description", ""))
                            else:
                                step_parts.append(str(s))
                        steps_text = " ".join(filter(None, step_parts))
                    else:
                        steps_text = str(steps_raw)
                    tc_texts.append(f"{scenario} {steps_text}".strip())

                tc_embs = self.model.encode(tc_texts)
                tc_similarities = cosine_similarity(new_req_emb, tc_embs)[0]

                for i, sim in enumerate(tc_similarities):
                    if sim >= (self.similarity_threshold - 0.1):
                        tc = existing_test_cases[i]
                        impacted_tcs.append({
                            "id":              tc.get("test_case_id", f"TC{i+1:03d}"),
                            "scenario":        tc.get("scenario", tc.get("title", "")),
                            "test_type":       tc.get("test_type", "Functional"),
                            "module":          tc.get("module", "General"),
                            "relevance_score": round(float(sim), 3),
                        })

            # 4. Derive impacted modules heuristically
            impacted_modules = self._extract_modules(new_requirement, impacted_sentences)

            result = {
                "impacted_modules":    impacted_modules,
                "impacted_test_cases": impacted_tcs,
                "impacted_prd_context": impacted_sentences,
                "total_impacted_tcs":  len(impacted_tcs),
            }
            logger.info(
                f"Impact analysis: {len(impacted_modules)} modules, "
                f"{len(impacted_tcs)} TCs impacted."
            )
            return result

        except Exception as e:
            logger.error(f"Error during impact analysis: {e}", exc_info=True)
            return {"impacted_modules": [], "impacted_test_cases": [], "error": str(e), "total_impacted_tcs": 0}

    def _extract_modules(self, new_req: str, impacted_sentences: List[Dict]) -> List[str]:
        """Heuristic module extraction from the new requirement and matched PRD text."""
        text_corpus = (
            new_req + " " + " ".join(s["sentence"] for s in impacted_sentences)
        ).lower()

        found = set()
        for module, keywords in _MODULE_KEYWORDS.items():
            if any(kw in text_corpus for kw in keywords):
                found.add(module)

        return sorted(found) if found else ["General/Core"]
