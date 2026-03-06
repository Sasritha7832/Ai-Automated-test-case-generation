"""
agents.py
---------
DISABLED — replaced by test_generator.py

CrewAI multi-agent orchestration has been removed in favour of a single
deterministic LLM generator pipeline.  This file is kept as a stub so
that any lingering imports don't cause ImportError crashes.
"""

from logger import get_logger

logger = get_logger(__name__)


def create_agents(feature: str, detected_modules: list = None):
    """
    STUB — no-op replacement for the removed CrewAI agent factory.
    Returns empty agents and tasks lists.
    Use test_generator.TestGenerator instead.
    """
    logger.warning(
        "create_agents() called on the disabled stub. "
        "Use test_generator.TestGenerator.generate_tests() instead."
    )
    return [], []