from logger import get_logger

logger = get_logger(__name__)

class TestPriorityModel:
    """Predicts Test Case Priority heuristically based on multi-dimensional features."""
    
    def predict_priority(self, test_case: dict, complexity_score: int, bug_risk_label: str) -> str:
        """
        Features evaluated:
        1. Base Test Category (Performance/Boundary = higher priority, Functional = base)
        2. Requirement Complexity Score (High complexity = higher priority)
        3. Associated Bug Risk Model Prediction (High Risk = higher priority)
        
        Returns Predicted Priority String (P0, P1, P2, P3)
        """
        try:
            score = 0
            
            # 1. Feature: Test Category Impact
            category = test_case.get("test_type", "Functional").lower()
            if "performance" in category or "security" in category:
                score += 4
            elif "edge" in category or "boundary" in category:
                score += 3
            elif "negative" in category:
                score += 2
            else:
                score += 1  # Functional/UI
                
            # 2. Feature: Complexity Score Impact
            if complexity_score > 70:
                score += 4
            elif complexity_score > 40:
                score += 2
            else:
                score += 1
                
            # 3. Feature: Bug Risk Prediction Impact
            if bug_risk_label == "High":
                score += 4
            elif bug_risk_label == "Medium":
                score += 2
            else:
                score += 0
                
            # Map absolute heuristic score back to standard Priorities
            if score >= 10:
                priority = "P0" # Critical path, complex logic, high risk
            elif score >= 7:
                priority = "P1" # High impact, edge cases, med risk
            elif score >= 4:
                priority = "P2" # Standard functional behavior
            else:
                priority = "P3" # Simple UI/Low impact
                
            logger.info(f"Test case '{test_case.get('test_case_id', 'TC')}' assigned predicted priority {priority} (Score: {score})")
            return priority
            
        except Exception as e:
            logger.error(f"Error predicting test priority: {e}", exc_info=True)
            return "P2" # safe fallback

    def assign_priorities(self, test_cases: list, complexity_score: int = 50, bug_risk_label: str = "Medium") -> list:
        """
        Batch method: assigns priority to all test cases in the list.
        Returns the updated list with 'priority' fields populated.
        """
        logger.info(f"Assigning priorities to {len(test_cases)} test cases.")
        for i, tc in enumerate(test_cases):
            if not tc.get("test_case_id"):
                tc["test_case_id"] = f"TC{i+1:03d}"
            tc["priority"] = self.predict_priority(tc, complexity_score, bug_risk_label)
        return test_cases

