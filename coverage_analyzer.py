from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from embedding_singleton import get_embedding_model
from logger import get_logger

logger = get_logger(__name__)


class CoverageAnalyzer:
    """
    Evaluates how well generated test cases cover the original PRD requirements
    using semantic similarity between requirement sentences and test case text.
    """

    def __init__(self, model_name=None):
        # Use shared singleton — no redundant model load
        self.model = get_embedding_model()

    def _tc_to_text(self, tc: dict) -> str:
        """
        Builds a rich text representation of a test case for semantic matching.
        Uses scenario + test_steps + expected_result + test_data.
        Handles both old schema (list 'steps') and new schema (list 'test_steps').
        """
        steps_raw = tc.get("test_steps", tc.get("steps", []))
        
        # Handle new format (list of dicts) vs old format (list of strings/single string)
        if isinstance(steps_raw, list):
            if steps_raw and isinstance(steps_raw[0], dict):
                steps_text = " ".join([s.get("description", "") for s in steps_raw])
            else:
                steps_text = " ".join([str(s) for s in steps_raw])
        else:
            steps_text = str(steps_raw)

        return " ".join(filter(None, [
            tc.get("scenario", ""),
            steps_text,
            tc.get("expected_result", ""),
            tc.get("test_data", ""),
            tc.get("preconditions", ""),
            tc.get("module", ""),
            tc.get("test_type", ""),
        ]))

    def analyze_coverage(self, prd_sentences: list, test_cases: list, threshold: float = 0.35) -> dict:
        """
        Maps PRD requirement paragraphs to generated test cases via cosine similarity.
        Returns a coverage dict with score (0-100), covered list, missing list,
        and coverage_percentage alias.
        """
        if not prd_sentences or not test_cases:
            logger.warning("Coverage analysis skipped: empty inputs.")
            return {
                "score": 0,
                "coverage_percentage": 0,
                "covered": [],
                "missing": prd_sentences or [],
                "total_requirements": len(prd_sentences or []),
                "covered_count": 0,
            }

        logger.info(
            f"Coverage: {len(prd_sentences)} PRD sentences vs {len(test_cases)} test cases."
        )

        tc_texts = [self._tc_to_text(tc) for tc in test_cases]

        try:
            req_embeddings = self.model.encode(prd_sentences, show_progress_bar=False)
            tc_embeddings = self.model.encode(tc_texts, show_progress_bar=False)

            sim_matrix = cosine_similarity(req_embeddings, tc_embeddings)

            covered = []
            missing = []
            rtm_mapping = []

            for i, req in enumerate(prd_sentences):
                # Skip noise and short lines
                if len(req.strip()) < 15:
                    continue
                
                req_sims = sim_matrix[i]
                max_sim = float(np.max(req_sims))
                
                # Build RTM mapping for this requirement
                linked_tcs = []
                for tc_idx, sim in enumerate(req_sims):
                    if sim >= threshold:
                        tc = test_cases[tc_idx]
                        linked_tcs.append({
                            "id": tc.get("test_case_id", f"TC{tc_idx+1}"),
                            "title": tc.get("title", tc.get("scenario", "Untitled")),
                            "similarity": round(float(sim), 3)
                        })
                
                if max_sim >= threshold:
                    covered.append(req)
                    rtm_mapping.append({
                        "req_id": f"REQ-{i+1:03d}",
                        "text": req,
                        "status": "Covered",
                        "linked_test_cases": linked_tcs
                    })
                else:
                    missing.append(req)
                    rtm_mapping.append({
                        "req_id": f"REQ-{i+1:03d}",
                        "text": req,
                        "status": "Uncovered",
                        "linked_test_cases": []
                    })

            total_valid = len(covered) + len(missing)
            score = round((len(covered) / total_valid * 100), 1) if total_valid > 0 else 0.0

            logger.info(f"Coverage: {score:.1f}% ({len(covered)}/{total_valid} requirements covered)")

            return {
                "score": score,
                "coverage_percentage": score,  # alias used by other modules
                "covered": covered,
                "missing": missing,
                "total_requirements": total_valid,
                "covered_count": len(covered),
                "rtm_mapping": rtm_mapping
            }

        except Exception as e:
            logger.error(f"Error in coverage analysis: {e}", exc_info=True)
            return {
                "score": 0,
                "coverage_percentage": 0,
                "covered": [],
                "missing": prd_sentences,
                "total_requirements": len(prd_sentences),
                "covered_count": 0,
                "rtm_mapping": []
            }
