from sklearn.metrics.pairwise import cosine_similarity
from embedding_singleton import get_embedding_model
from logger import get_logger

logger = get_logger(__name__)


class DeduplicationEngine:
    """Removes duplicate or highly similar test cases using semantic embeddings."""

    def __init__(self):
        # Use shared singleton — no redundant model load
        self.model = get_embedding_model()

    def _tc_to_text(self, tc: dict) -> str:
        """Builds a rich text representation for semantic similarity."""
        steps_raw = tc.get("steps", tc.get("test_steps", []))
        if isinstance(steps_raw, list):
            step_parts = [
                s.get("description", "") if isinstance(s, dict) else str(s)
                for s in steps_raw
            ]
            steps_text = " ".join(filter(None, step_parts))
        elif isinstance(steps_raw, str):
            steps_text = steps_raw
        else:
            steps_text = ""

        return " ".join(filter(None, [
            tc.get("scenario", tc.get("title", "")),
            steps_text,
            tc.get("expected_result", ""),
            tc.get("module", ""),
            tc.get("test_type", ""),
        ]))

    def deduplicate(self, test_cases: list, similarity_threshold: float = 0.88) -> tuple:
        """
        Returns (unique_test_cases, removed_count).
        Uses cosine similarity on shared embedding model.
        """
        initial_count = len(test_cases)
        if initial_count <= 1:
            return test_cases, 0

        logger.info(f"Deduplicating {initial_count} test cases...")
        tc_texts = [self._tc_to_text(tc) for tc in test_cases]

        try:
            embeddings = self.model.encode(tc_texts, show_progress_bar=False, batch_size=64)
            sim_matrix = cosine_similarity(embeddings)

            unique_cases = []
            drop_indices = set()

            for i in range(initial_count):
                if i in drop_indices:
                    continue
                unique_cases.append(test_cases[i])
                for j in range(i + 1, initial_count):
                    if sim_matrix[i, j] >= similarity_threshold:
                        drop_indices.add(j)

            removed_count = initial_count - len(unique_cases)
            logger.info(f"Dedup: removed {removed_count}, kept {len(unique_cases)}.")
            return unique_cases, removed_count

        except Exception as e:
            logger.error(f"Deduplication error: {e}", exc_info=True)
            return test_cases, 0
