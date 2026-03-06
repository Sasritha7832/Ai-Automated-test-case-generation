import re
import json
import numpy as np
from typing import List
from config import Config
from logger import get_logger

# Section 2: Updated to use langchain-ollama instead of deprecated langchain_community
try:
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    try:
        from langchain_community.llms import Ollama
    except ImportError:
        Ollama = None

logger = get_logger(__name__)

# Hard cap on modules — prevents module explosion (Section 6)
MAX_MODULES = Config.MAX_MODULES

# ─── Rule-based module keyword map ───────────────────────────────────────────
MODULE_KEYWORDS = {
    "Authentication":   ["login", "logout", "sign in", "sign up", "register", "password",
                         "jwt", "token", "oauth", "session", "credentials", "2fa", "mfa",
                         "forgot password", "reset password", "authentication", "auth"],
    "User Profile":     ["profile", "account", "user details", "avatar", "preferences",
                         "settings", "personal info", "update account"],
    "Product Catalog":  ["product", "catalog", "category", "listing", "item", "sku",
                         "inventory", "stock", "product page", "product detail"],
    "Search":           ["search", "filter", "sort", "query", "find", "browse",
                         "autocomplete", "suggestion", "facet"],
    "Shopping Cart":    ["cart", "basket", "add to cart", "remove from cart",
                         "cart total", "quantity", "wishlist"],
    "Checkout":         ["checkout", "place order", "shipping", "delivery", "address",
                         "billing", "order summary", "coupon", "promo code", "discount"],
    "Payment":          ["payment", "pay", "credit card", "debit card", "upi", "wallet",
                         "transaction", "refund", "pgw", "gateway", "stripe", "razorpay"],
    "Order Management": ["order", "order history", "order status", "track order",
                         "cancel order", "return", "invoice", "receipt"],
    "Notifications":    ["notification", "email", "sms", "push notification", "alert",
                         "otp", "message"],
    "Admin Dashboard":  ["admin", "dashboard", "manage", "report", "analytics",
                         "role", "permission", "user management"],
    # API Layer and Performance remain in the keyword map for coverage but
    # are filtered out of the detected-modules list (Section 4)
    "API Layer":        ["api", "endpoint", "request", "response", "rest", "graphql",
                         "webhook", "swagger", "rate limit", "throttle"],
    "Performance":      ["concurrent", "load", "stress", "latency", "throughput",
                         "caching", "cdn", "response time", "scalability"],
}

# Section 4: Modules that should not appear as standalone feature modules in the QA plan.
# They are cross-cutting concerns that will be covered by test_type categories instead.
IGNORED_MODULES = {"API Layer", "Performance", "Security"}

ALL_TESTING_TYPES = [
    "Functional", "Negative", "Boundary", "Edge Case",
    "Integration", "Performance", "Security", "UI", "API", "Regression",
    "Data Validation", "Accessibility",
]


def _merge_similar_modules(modules: List[str]) -> List[str]:
    """
    Merge semantically similar modules using embedding cosine similarity.
    Threshold: 0.80.  Keeps the first occurrence and removes duplicates.
    Example: ["Checkout", "Payment"] might merge to ["Checkout"].
    """
    if len(modules) <= 1:
        return modules
    try:
        from embedding_singleton import get_embedding_model
        from sklearn.metrics.pairwise import cosine_similarity

        model = get_embedding_model()
        embeddings = model.encode(modules, show_progress_bar=False)
        sim_matrix = cosine_similarity(embeddings)

        merged = []
        skip = set()
        for i, mod in enumerate(modules):
            if i in skip:
                continue
            merged.append(mod)
            for j in range(i + 1, len(modules)):
                if j not in skip and sim_matrix[i][j] >= 0.80:
                    logger.info(
                        f"Module merge: '{modules[j]}' → '{mod}' "
                        f"(sim={sim_matrix[i][j]:.2f})"
                    )
                    skip.add(j)
        return merged

    except Exception as e:
        logger.warning(f"Module merge skipped (embedding error): {e}")
        return modules


def detect_modules_from_context(context: str) -> list:
    """
    Extracts modules from PRD section headers.
    Falls back to regular keyword scanning if header extraction yields few results.
    Filters out cross-cutting concern pseudo-modules (IGNORED_MODULES).
    Caps at MAX_MODULES and merges similar modules.
    """
    detected = set()

    # Extract potential headers (e.g., # Authentication, 1. Product Catalog)
    headers = re.findall(r'^(?:#+|\d+\.)\s*(.+)$', context, re.MULTILINE)

    if headers:
        for header in headers:
            header_lower = header.lower()
            for module, keywords in MODULE_KEYWORDS.items():
                if any(kw in header_lower for kw in keywords):
                    detected.add(module)

    # Fallback to scanning the whole PRD if header extraction finds < 2 modules
    if len(detected) < 2:
        context_lower = context.lower()
        for module, keywords in MODULE_KEYWORDS.items():
            if any(kw in context_lower for kw in keywords):
                detected.add(module)

    # Remove non-functional cross-cutting pseudo-modules
    detected -= IGNORED_MODULES

    if not detected:
        detected.add("Core Module")

    result = sorted(list(detected))

    # Merge similar modules (avoids "Checkout" + "Payment" doubling)
    result = _merge_similar_modules(result)

    # Cap at MAX_MODULES (Section 6 safeguard)
    if len(result) > MAX_MODULES:
        logger.info(
            f"Module cap applied: {len(result)} → {MAX_MODULES} modules "
            f"(dropped: {result[MAX_MODULES:]})"
        )
        result = result[:MAX_MODULES]

    logger.info(f"Module detection final: {result}")
    return result


def detect_testing_types_from_context(context: str, modules: list) -> list:
    """
    Determine which testing types apply based on module types and PRD keywords.
    Always returns the full set when in doubt.
    """
    ctx = context.lower()
    types = {"Functional", "Negative", "Regression"}  # Always include these 3
    if any(m in modules for m in ["Authentication", "Payment"]):
        types.update(["Security", "API"])
    if any(kw in ctx for kw in ["concurrent", "load", "latency", "throughput"]):
        types.add("Performance")
    if any(kw in ctx for kw in ["ui", "interface", "screen", "button", "form", "page"]):
        types.add("UI")
    if any(m in modules for m in ["Shopping Cart", "Checkout", "Order Management", "Payment"]):
        types.update(["Integration", "Boundary", "Edge Case"])
    if any(kw in ctx for kw in ["limit", "maximum", "minimum", "range", "constraint"]):
        types.update(["Boundary", "Edge Case"])
    if len(types) < 8:
        types = set(ALL_TESTING_TYPES)
    return sorted(list(types))


class QAPlanner:
    """
    Pre-generation testing strategy planner.
    Uses rule-based module detection + optional LLM enrichment.
    LLM is lazy-loaded to prevent startup blocking.
    """

    def __init__(self):
        self._llm = None
        self._llm_tried = False
        logger.info("QAPlanner created (LLM lazy-loaded on first use).")

    def _get_llm(self):
        """Lazy-load Ollama LLM — only when needed for summary enrichment."""
        if self._llm_tried:
            return self._llm
        self._llm_tried = True
        if Ollama is None:
            return None
        try:
            self._llm = Ollama(model=Config.OLLAMA_MODEL, temperature=0.3)
            logger.info(f"QAPlanner LLM loaded: {Config.OLLAMA_MODEL}")
        except Exception as e:
            logger.warning(f"QAPlanner LLM unavailable (rule-based fallback active): {e}")
            self._llm = None
        return self._llm

    def generate_plan(self, context: str) -> dict:
        """
        Returns a structured QA plan dict.
        Uses rule-based detection first, optionally enriches with LLM summary.
        """
        logger.info("Generating QA plan...")

        # ── Rule-based detection (always runs, crash-safe) ────────────────────
        modules = detect_modules_from_context(context)
        testing_types = detect_testing_types_from_context(context, modules)

        # Risk indicators from known high-risk keywords
        risk_indicators = []
        ctx = context.lower()
        risk_kws = {
            "Concurrent access may introduce race conditions": ["concurrent", "race", "thread"],
            "Authentication bypass risk detected": ["auth", "bypass", "token", "session"],
            "Input validation required for user-submitted fields": ["input", "form", "upload"],
            "Payment flow requires PCI-DSS compliance checks": ["payment", "credit card", "transaction"],
            "SQL injection risk in search/filter parameters": ["search", "query", "filter", "param"],
            "API rate limiting must be enforced": ["api", "endpoint", "rate limit", "throttle"],
            "Data encryption required for sensitive fields": ["password", "personal", "sensitive", "encrypt"],
        }
        for indicator, triggers in risk_kws.items():
            if any(t in ctx for t in triggers):
                risk_indicators.append(indicator)
        if not risk_indicators:
            risk_indicators = [
                "Review all user-facing inputs for validation",
                "Verify error handling on all API calls",
            ]

        base_plan = {
            "modules_detected": modules,
            "recommended_testing_types": testing_types,
            "risk_indicators": risk_indicators[:5],
            "scenario_counts": {
                "Functional": "8–12 scenarios",
                "Negative": "6–8 scenarios",
                "Boundary": "4–6 scenarios",
                "Edge Case": "4–6 scenarios",
                "Integration": "4–6 scenarios",
                "Performance": "3–4 scenarios",
                "Security": "4–6 scenarios",
                "UI": "4–5 scenarios",
                "API": "4–6 scenarios",
                "Regression": "4–6 scenarios",
                "Data Validation": "3–4 scenarios",
                "Accessibility": "2–3 scenarios",
            },
            "summary": (
                f"Testing strategy for {len(modules)} module(s): {', '.join(modules)}. "
                f"Will cover all 12 testing dimensions generating 40–120 structured test cases."
            ),
        }

        # ── Optional LLM enrichment for summary ───────────────────────────────
        llm = self._get_llm()
        if llm:
            try:
                prompt = (
                    "You are a Principal QA Architect.\n"
                    "Given the PRD context below, write ONE paragraph executive testing strategy summary.\n"
                    "Be specific about the risks identified and the testing approach.\n"
                    "Do NOT output JSON, just plain text.\n\n"
                    f"PRD Context (first 1500 chars):\n{context[:1500]}"
                )
                summary = llm.invoke(prompt)
                if summary and len(summary.strip()) > 30:
                    base_plan["summary"] = summary.strip()
                    logger.info("LLM enriched QA plan summary.")
            except Exception as e:
                logger.warning(f"LLM enrichment skipped: {e}")

        logger.info(f"QA Plan: {len(modules)} modules, {len(testing_types)} test types.")
        return base_plan
