"""
crew_setup.py
-------------
DISABLED — replaced by test_generator.py

CrewAI Crew kickoff logic has been removed.  This stub is kept so that
any code that still imports run_crew() gets a safe no-op rather than
an ImportError.
"""

from logger import get_logger

logger = get_logger(__name__)


def run_crew(feature: str, context: str) -> str:
    """
    STUB — deprecated.  Returns empty string.
    Use test_generator.TestGenerator.generate_tests() instead.
    """
    logger.warning(
        "run_crew() is deprecated and has been replaced by "
        "TestGenerator.generate_tests(). Returning empty string."
    )
    return ""