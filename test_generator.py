"""
test_generator.py
-----------------
Deterministic, single-pass LLM test case generator.
Replaces CrewAI multi-agent orchestration.

Pipeline: requirements list → Ollama LLM → JSON test cases

Design principles:
- One LLM call per batch of requirements (fast, deterministic)
- 7 test categories per requirement: Functional, Negative, Edge Case,
  Boundary, Security, Performance, Integration
- Min 6 tests per requirement → 60–120 tests per PRD
- Robust JSON extraction with fallback sanitizer
- Model priority: llama3:8b → gemma3:4b
"""

import json
import re
import requests
import time
from typing import List, Dict, Any
from config import Config
from logger import get_logger

logger = get_logger("TestGenerator")

# ── Constants ────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
BATCH_SIZE = 2          # Requirements per LLM call (smaller = faster + more reliable JSON)
REQUEST_TIMEOUT = 180   # Seconds per Ollama call (generous for slow machines)

# Test categories to generate per requirement
TEST_CATEGORIES = [
    "Functional",
    "Negative",
    "Edge Case",
    "Boundary",
    "Security",
    "Performance",
    "Integration",
]

# JSON schema shown to the LLM
_JSON_SCHEMA = """\
Return ONLY a valid JSON array. No markdown, no explanations.
Each object MUST have exactly these keys:
{
  "test_case_id": "TC001",
  "title": "Descriptive test title",
  "module": "Module name (from section heading)",
  "test_type": "Functional",
  "priority": "P1",
  "severity": "High",
  "preconditions": "Setup state required",
  "test_steps": [
    {"step_no": 1, "description": "Step action", "test_data": "value", "expected_result": "outcome"},
    {"step_no": 2, "description": "Step action", "test_data": "", "expected_result": "outcome"}
  ],
  "test_data": "realistic test data values",
  "expected_result": "Specific, measurable result",
  "actual_result": "",
  "status": "Not Executed",
  "bug_id": "",
  "notes": ""
}

Rules:
- test_type: one of [Functional, Negative, Boundary, Edge Case, Integration, Performance, Security]
- priority: P0 (Security/Performance critical), P1 (Negative/Integration/Boundary), P2 (Functional), P3 (Edge Case/UI)
- severity: P0→Critical, P1→High, P2→Medium, P3→Low
- test_steps: 3–5 steps, each with realistic test_data and expected_result
- test_data: real values (emails, passwords, amounts) not "N/A"
- expected_result: specific outcome (not "success" or "works")
- actual_result, bug_id, notes: always empty string ""
- status: always "Not Executed"
"""


class TestGenerator:
    """
    Single deterministic LLM test case generator.
    Replaces CrewAI — no agents, no retries, no orchestration overhead.
    """

    def __init__(self):
        self._model: str = None
        logger.info("TestGenerator initialized.")

    # ── Model resolution ─────────────────────────────────────────────────────

    def _resolve_model(self) -> str:
        """Try models in priority order; cache the first one that responds."""
        if self._model:
            return self._model
        candidates = [
            getattr(Config, "PRIMARY_LLM_MODEL", "llama3:8b"),
            getattr(Config, "FALLBACK_LLM_MODEL", "gemma3:4b"),
        ]
        for model in candidates:
            try:
                resp = requests.get(
                    "http://localhost:11434/api/tags", timeout=5
                )
                if resp.status_code == 200:
                    available = [m["name"] for m in resp.json().get("models", [])]
                    # Match by prefix (e.g. "llama3:8b" or "llama3")
                    for avail in available:
                        if avail.startswith(model.split(":")[0]):
                            self._model = avail
                            logger.info(f"TestGenerator: using model '{self._model}'.")
                            return self._model
            except Exception:
                pass
        # Fallback: use config default without verification
        self._model = Config.OLLAMA_MODEL
        logger.warning(f"TestGenerator: cannot verify models; defaulting to '{self._model}'.")
        return self._model

    # ── Ollama call ──────────────────────────────────────────────────────────

    def _call_ollama(self, prompt: str) -> str:
        """Send a prompt to Ollama and return the raw text response."""
        model = self._resolve_model()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.25,
                "num_predict": 4096,
                "top_p": 0.9,
            },
        }
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.exceptions.ConnectionError:
            logger.error("Ollama is not running. Start Ollama and try again.")
            raise RuntimeError(
                "Ollama is not running. Start with: ollama serve"
            )
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise

    # ── JSON extraction ──────────────────────────────────────────────────────

    def _extract_json(self, raw: str) -> List[Dict]:
        """Extract a JSON array from LLM output — handles markdown fences."""
        # Strip markdown code fences
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()

        # Find the outermost JSON array
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end == -1 or end <= start:
            logger.warning("No JSON array found in LLM response.")
            return []

        json_str = cleaned[start : end + 1]

        # Try direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Sanitize: remove trailing commas before } or ]
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed after sanitization: {e}")
            return []

    # ── Prompt builder ───────────────────────────────────────────────────────

    def _build_prompt(
        self,
        requirements: List[Dict],
        feature_name: str,
        context: str,
    ) -> str:
        """Build a focused prompt for a batch of requirements."""
        req_lines = "\n".join(
            f"{i+1}. [{r.get('section_title', 'General')}] {r.get('requirement_text', r.get('text', str(r)))}"
            for i, r in enumerate(requirements)
        )
        num_reqs = len(requirements)
        min_tests = num_reqs * 3   # 3 minimum per requirement (achievable for small models)
        max_tests = num_reqs * 6   # 6 maximum per requirement

        return f"""You are a senior QA engineer. Generate test cases for: "{feature_name}".

Requirements ({num_reqs}):
{req_lines}

Context:
{context[:800]}

Generate {min_tests}–{max_tests} test cases. For each requirement include: Functional, Negative, Security tests minimum.
Use the section heading as the "module" field.

{_JSON_SCHEMA}

Start your response immediately with '['. No other text."""

    # ── Schema normalizer ────────────────────────────────────────────────────

    def _normalize(self, tc: Dict, index: int, feature_name: str) -> Dict:
        """Ensure a test case has all required fields with correct types."""
        steps = tc.get("test_steps", tc.get("steps", []))
        if isinstance(steps, str):
            steps = [
                {"step_no": i + 1, "description": s.strip(), "test_data": "", "expected_result": ""}
                for i, s in enumerate(steps.split("\n"))
                if s.strip()
            ]
        elif isinstance(steps, list):
            normalized_steps = []
            for i, s in enumerate(steps):
                if isinstance(s, str):
                    normalized_steps.append({
                        "step_no": i + 1,
                        "description": s,
                        "test_data": "",
                        "expected_result": "",
                    })
                elif isinstance(s, dict):
                    normalized_steps.append({
                        "step_no": s.get("step_no", i + 1),
                        "description": s.get("description", str(s)),
                        "test_data": s.get("test_data", ""),
                        "expected_result": s.get("expected_result", ""),
                    })
            steps = normalized_steps

        if not steps:
            steps = [{"step_no": 1, "description": "Execute the test", "test_data": "", "expected_result": "Expected behavior observed"}]

        priority = str(tc.get("priority", "P2"))
        test_type = str(tc.get("test_type", "Functional"))
        sev_map = {"P0": "Critical", "P1": "High", "P2": "Medium", "P3": "Low"}

        return {
            "test_case_id": f"TC{index:03d}",
            "title": tc.get("title", tc.get("scenario", f"Test Case {index}")),
            "scenario": tc.get("title", tc.get("scenario", f"Test Case {index}")),
            "module": tc.get("module", feature_name),
            "test_type": test_type,
            "priority": priority,
            "severity": tc.get("severity") or sev_map.get(priority, "Medium"),
            "preconditions": tc.get("preconditions", ""),
            "test_steps": steps,
            "test_data": tc.get("test_data", ""),
            "expected_result": tc.get("expected_result", ""),
            "actual_result": "",
            "status": "Not Executed",
            "bug_id": "",
            "notes": tc.get("notes", ""),
        }

    # ── Public API ───────────────────────────────────────────────────────────

    def generate_tests(
        self,
        feature_name: str,
        context: str,
        requirements: List[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate test cases for a feature.

        Args:
            feature_name: The feature being tested (e.g., "Authentication")
            context: Full PRD context text from RAG retrieval
            requirements: Optional list of extracted requirement dicts.
                          Each dict has keys: requirement_text, section_title, module
                          If None, falls back to generating from raw context.

        Returns:
            List of normalized test case dicts.
        """
        logger.info(f"TestGenerator: generating tests for '{feature_name}'...")
        start = time.time()

        all_test_cases = []
        tc_counter = 1

        if not requirements:
            # Fallback: treat the whole context as a single pseudo-requirement
            requirements = [{"requirement_text": context[:2000], "section_title": feature_name, "module": feature_name}]
            logger.warning("No structured requirements provided; using full context as fallback.")

        logger.info(f"Generating tests for {len(requirements)} requirements in batches of {BATCH_SIZE}.")

        # Process in batches
        for batch_start in range(0, len(requirements), BATCH_SIZE):
            batch = requirements[batch_start : batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(requirements) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"Batch {batch_num}/{total_batches}: {len(batch)} requirements...")

            try:
                prompt = self._build_prompt(batch, feature_name, context)
                raw = self._call_ollama(prompt)
                parsed = self._extract_json(raw)

                if parsed:
                    for tc in parsed:
                        normalized = self._normalize(tc, tc_counter, feature_name)
                        all_test_cases.append(normalized)
                        tc_counter += 1
                    logger.info(f"Batch {batch_num}: parsed {len(parsed)} test cases.")
                else:
                    logger.warning(f"Batch {batch_num}: no test cases parsed from LLM output.")
                    # Generate rule-based fallback tests for this batch
                    fallback = self._rule_based_fallback(batch, feature_name, tc_counter)
                    all_test_cases.extend(fallback)
                    tc_counter += len(fallback)
                    logger.info(f"Batch {batch_num}: generated {len(fallback)} rule-based fallback tests.")

            except RuntimeError:
                # Ollama not running — generate rule-based tests for entire PRD
                logger.error("Ollama unavailable — using full rule-based generation.")
                fallback = self._rule_based_fallback(requirements, feature_name, tc_counter)
                return fallback

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}", exc_info=True)
                # Continue with next batch rather than failing completely
                continue

        elapsed = round(time.time() - start, 2)
        logger.info(
            f"TestGenerator: completed in {elapsed}s. "
            f"Generated {len(all_test_cases)} test cases from {len(requirements)} requirements."
        )
        return all_test_cases

    # ── Rule-based fallback ──────────────────────────────────────────────────

    def _rule_based_fallback(
        self,
        requirements: List[Dict],
        feature_name: str,
        start_idx: int = 1,
    ) -> List[Dict]:
        """
        Generate minimal but valid test cases without LLM, as a last resort.
        Produces 6 tests per requirement across 6 categories.
        """
        logger.info(f"Rule-based fallback: generating for {len(requirements)} requirements.")
        results = []
        idx = start_idx

        type_templates = [
            ("Functional", "P2", "Verify {req} works correctly with valid inputs"),
            ("Negative", "P1", "Verify {req} rejects invalid inputs with proper error message"),
            ("Edge Case", "P3", "Verify {req} handles empty or null inputs"),
            ("Boundary", "P1", "Verify {req} at minimum and maximum allowed values"),
            ("Security", "P0", "Verify {req} is not vulnerable to injection attacks"),
            ("Integration", "P1", "Verify {req} integrates correctly with dependent modules"),
        ]
        sev_map = {"P0": "Critical", "P1": "High", "P2": "Medium", "P3": "Low"}

        for req in requirements:
            req_text = req.get("requirement_text", str(req))[:100]
            module = req.get("section_title", feature_name)

            for test_type, priority, title_tmpl in type_templates:
                title = title_tmpl.format(req=req_text[:60])
                results.append({
                    "test_case_id": f"TC{idx:03d}",
                    "title": title,
                    "scenario": title,
                    "module": module,
                    "test_type": test_type,
                    "priority": priority,
                    "severity": sev_map[priority],
                    "preconditions": "System is running and accessible",
                    "test_steps": [
                        {"step_no": 1, "description": "Set up test environment", "test_data": "", "expected_result": "Environment ready"},
                        {"step_no": 2, "description": f"Execute: {req_text[:80]}", "test_data": "Standard test data", "expected_result": "System responds as expected"},
                        {"step_no": 3, "description": "Verify the result matches expected behavior", "test_data": "", "expected_result": "Result validated successfully"},
                    ],
                    "test_data": "Standard test data",
                    "expected_result": f"The system correctly handles: {req_text[:80]}",
                    "actual_result": "",
                    "status": "Not Executed",
                    "bug_id": "",
                    "notes": "Auto-generated (LLM unavailable)",
                })
                idx += 1

        logger.info(f"Rule-based fallback: generated {len(results)} test cases.")
        return results
