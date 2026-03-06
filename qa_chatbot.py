"""
qa_chatbot.py
-------------
RAG-grounded conversational QA assistant.
LLM loaded lazily on first question — startup never blocks.
"""

import json
from config import Config
from logger import get_logger

logger = get_logger(__name__)

def _make_llm(model_name: str):
    """Create an OllamaLLM (langchain_ollama) with fallback to langchain_community."""
    try:
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=model_name, temperature=0.3)
    except ImportError:
        from langchain_community.llms import Ollama
        return Ollama(model=model_name, temperature=0.3)


_CANDIDATE_MODELS = [
    getattr(Config, "PRIMARY_LLM_MODEL", "llama3:8b"),
    "llama3",
    getattr(Config, "FALLBACK_LLM_MODEL", "gemma3:4b"),
    "gemma:2b",
    "mistral",
    "phi3",
]


class QAChatbot:
    """
    Multi-context RAG-grounded QA assistant.
    LLM is loaded lazily on first use — startup never blocks.
    """

    def __init__(self):
        self.llm = None
        self._llm_tried = False
        logger.info("QAChatbot created (LLM will be loaded on first ask).")

    def _ensure_llm(self):
        """Lazy-load the LLM using langchain_ollama. Tries multiple models."""
        if self._llm_tried:
            return
        self._llm_tried = True

        for model in _CANDIDATE_MODELS:
            try:
                logger.info(f"QAChatbot: trying model '{model}'...")
                llm = _make_llm(model)
                test = llm.invoke("hi")
                if test:
                    self.llm = llm
                    logger.info(f"QAChatbot: using model '{model}'.")
                    return
            except Exception as e:
                logger.warning(f"Model '{model}' unavailable: {e}")

        logger.error(
            "QAChatbot: no Ollama model available. "
            "Start Ollama and pull a model (e.g. 'ollama pull llama3')."
        )

    # ── Context builders ───────────────────────────────────────────────────────

    def _prd_context(self, question: str, rag_pipeline) -> str:
        """Retrieve top-k PRD chunks relevant to the question."""
        if not rag_pipeline:
            return ""
        try:
            ctx = rag_pipeline.retrieve_feature_context(question)
            if ctx and len(ctx) > 20:
                return ctx[:3000]
        except Exception as e:
            logger.warning(f"PRD retrieval failed: {e}")
        try:
            all_texts = rag_pipeline.vector_store.get_all_texts()
            return " ".join(all_texts)[:3000] if all_texts else ""
        except Exception:
            return ""

    def _tc_context(self, question: str, test_cases: list) -> str:
        """Return a short summary of the most relevant test cases."""
        if not test_cases:
            return ""
        q = question.lower()
        relevant = []
        for tc in test_cases:
            text = (
                tc.get("scenario", tc.get("title", "")) + " " +
                tc.get("module", "") + " " +
                tc.get("test_type", "")
            ).lower()
            if any(word in text for word in q.split() if len(word) > 3):
                relevant.append(tc)
        sample = relevant[:15] if relevant else test_cases[:10]
        lines = []
        for tc in sample:
            lines.append(
                f"[{tc.get('test_case_id','?')}] {tc.get('module','?')} | "
                f"{tc.get('test_type','?')} | P:{tc.get('priority','?')} | "
                f"{tc.get('scenario', tc.get('title','?'))}"
            )
        return "\n".join(lines)

    def _plan_context(self, qa_plan: dict) -> str:
        if not qa_plan:
            return ""
        return (
            f"Modules: {', '.join(qa_plan.get('modules_detected', []))}\n"
            f"Testing Types: {', '.join(qa_plan.get('recommended_testing_types', []))}\n"
            f"Risk Indicators: {', '.join(qa_plan.get('risk_indicators', []))}"
        )

    def _coverage_context(self, prd_sentences: list, coverage_analyzer) -> str:
        if not prd_sentences or not coverage_analyzer:
            return ""
        return ""  # Skip live coverage re-computation in chatbot (too slow)

    def _bug_risk_context(self, last_report: dict) -> str:
        if not last_report:
            return ""
        scenarios = last_report.get("bug_risk", {}).get("scenarios", [])
        if not scenarios:
            return ""
        lines = [f"- [{s.get('risk_level','?')}] {s.get('description','')}" for s in scenarios[:5]]
        return "\n".join(lines)

    # ── Main ask method ────────────────────────────────────────────────────────

    def ask(
        self,
        question: str,
        chat_history: list = None,
        rag_pipeline=None,
        test_cases: list = None,
        qa_plan: dict = None,
        prd_sentences: list = None,
        coverage_analyzer=None,
        last_report: dict = None,
    ) -> str:
        self._ensure_llm()

        if not self.llm:
            return (
                "⚠️ **Ollama is not running or no model is available.**\n\n"
                "To enable the AI assistant:\n"
                "1. Install Ollama: https://ollama.ai\n"
                "2. Run: `ollama pull llama3`\n"
                "3. Restart Streamlit\n\n"
                "While Ollama is unavailable, use the Analytics Dashboard and "
                "Test Suite tabs to explore your generated test cases."
            )

        # Build context
        prd_ctx  = self._prd_context(question, rag_pipeline)
        tc_ctx   = self._tc_context(question, test_cases or [])
        plan_ctx = self._plan_context(qa_plan or {})
        risk_ctx = self._bug_risk_context(last_report or {})

        context_block = ""
        if prd_ctx:
            context_block += f"\n### PRD Context\n{prd_ctx}\n"
        if tc_ctx:
            context_block += f"\n### Relevant Test Cases\n{tc_ctx}\n"
        if plan_ctx:
            context_block += f"\n### QA Strategy\n{plan_ctx}\n"
        if risk_ctx:
            context_block += f"\n### Bug Risk Scenarios\n{risk_ctx}\n"

        # Format recent chat history (last 4 turns)
        history_block = ""
        if chat_history:
            for msg in chat_history[-4:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_block += f"{role}: {msg.get('content','')}\n"

        prompt = f"""You are an AI QA automation assistant. Answer based ONLY on the context provided below.
If the context does not contain enough information, say so clearly. Do not hallucinate.

{context_block}

{f'Recent conversation:{chr(10)}{history_block}' if history_block else ''}

User question: {question}

Answer concisely and specifically. Use bullet points where helpful."""

        try:
            answer = self.llm.invoke(prompt)
            return str(answer).strip()
        except Exception as e:
            logger.error(f"Chatbot LLM error: {e}", exc_info=True)
            return f"⚠️ Error generating response: {e}\n\nPlease check that Ollama is running."

    def get_suggested_questions(self, test_cases: list, qa_plan: dict) -> list:
        """Returns suggested questions based on current pipeline state."""
        suggestions = [
            "Which modules have the highest bug risk?",
            "What security tests were generated?",
            "Which requirements have low coverage?",
            "What edge cases exist for the checkout flow?",
            "List all performance tests generated.",
            "What are the top authentication vulnerabilities?",
        ]
        if qa_plan:
            modules = qa_plan.get("modules_detected", [])
            if modules:
                suggestions.insert(0, f"What test cases exist for {modules[0]}?")
        return suggestions[:8]
