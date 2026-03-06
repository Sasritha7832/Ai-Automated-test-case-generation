import json
import re
from logger import get_logger

logger = get_logger(__name__)

def parse_testcases(output):
    """
    Robustly parses LLM raw output into a list of test case dicts.
    Handles:
    - Clean JSON arrays
    - JSON wrapped in ```json ... ``` markdown blocks
    - JSON arrays embedded anywhere inside verbose LLM prose
    """
    logger.info("Parsing structured test cases from raw LLM output.")

    if not output:
        logger.warning("Empty output received for parsing.")
        return None

    # ── Attempt 1: Direct parse (already clean JSON) ──────────────────────────
    cleaned = output.strip()
    # Remove markdown fences if present
    cleaned = re.sub(r"```json\s*", "", cleaned)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) > 0:
            logger.info(f"Direct parse succeeded: {len(data)} test cases.")
            return data
    except Exception:
        pass

    # ── Attempt 2: Extract the largest [...] block from anywhere in the text ──
    try:
        # Find the first '[' and last ']' to extract the outermost JSON array
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start:end + 1]
            data = json.loads(candidate)
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Bracket-scan parse succeeded: {len(data)} test cases.")
                return data
    except Exception:
        pass

    # ── Attempt 3: Find all {...} objects individually and collect them ────────
    try:
        objects = re.findall(r'\{[^{}]+(?:\{[^{}]*\}[^{}]*)?\}', cleaned, re.DOTALL)
        parsed_list = []
        for obj_str in objects:
            try:
                obj = json.loads(obj_str)
                if isinstance(obj, dict) and ("test_type" in obj or "title" in obj or "scenario" in obj):
                    parsed_list.append(obj)
            except Exception:
                pass
        if parsed_list:
            logger.info(f"Object-scan parse succeeded: {len(parsed_list)} test cases.")
            return parsed_list
    except Exception:
        pass

    logger.error(f"All parse attempts failed. Output snippet: {output[:200]}")
    return None