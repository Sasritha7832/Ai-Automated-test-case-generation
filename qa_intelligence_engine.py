from typing import Dict, Any, List
from logger import get_logger

logger = get_logger(__name__)

ALL_TESTING_TYPES = {
    "Functional", "Negative", "Boundary", "Edge Case",
    "Integration", "Performance", "Security", "UI", "API", "Regression"
}

# Types with highest impact on quality
HIGH_VALUE_TYPES = {"Security", "Performance", "Boundary", "Edge Case", "Integration"}


class QAIntelligenceEngine:
    """
    Aggregates analytics signals to produce a unified QA Intelligence Score (0-100).

    Weights per specification:
      - PRD Coverage       35%
      - Test Diversity     25%
      - Security Coverage  10%
      - Performance Tests  10%
      - Req Traceability   10%
      - Bug Risk (inverse)  5%
      - PRD Quality         5%
      Total              = 100%

    Score is completely deterministic for identical inputs.
    """

    def __init__(self):
        # Weights per specification: sum = 1.00
        self.weights = {
            "coverage":     0.35,  # 35% — PRD requirement coverage
            "diversity":    0.25,  # 25% — variety of test types (out of 10)
            "security":     0.10,  # 10% — security tests present
            "performance":  0.10,  # 10% — performance tests present
            "traceability": 0.10,  # 10% — requirement traceability completeness
            "bug_risk":     0.05,  # 5%  — inverted bug risk (low risk = high score)
            "prd_quality":  0.05,  # 5%  — PRD quality (chunk count / context richness)
        }

    def calculate_score(
        self,
        coverage_percentage: float = 0.0,
        avg_bug_risk: float = 50.0,
        complexity_score: float = 0.0,
        test_categories: int = 1,
        test_cases: list = None,
        prd_chunk_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculates QA Intelligence Score from 0 to 100.
        Deterministic: identical inputs always produce the same output.

        Args:
            coverage_percentage: % of PRD requirements covered (0-100)
            avg_bug_risk: estimated bug risk percentage (0-100). Higher = worse.
            complexity_score: NLP complexity (0-10). Higher = more complex.
            test_categories: number of unique test types in the suite
            test_cases: list of test case dicts (used for type-specific scoring)
            prd_chunk_count: number of chunks in the PRD vector store (richness proxy)
        """
        test_cases = test_cases or []
        try:
            # ── 1. Coverage score (0-100) ─────────────────────────────────────
            cov_score = min(max(coverage_percentage, 0.0), 100.0)

            # ── 1.5. Traceability score (0-100) ──────────────────────────────
            # Traceability approaches 100 as coverage and test count both increase.
            trace_score = min(cov_score * 1.05, 100.0)

            # ── 2. Test Diversity score (0-100) ───────────────────────────────
            # Full 100 if all 10 types are present; partial otherwise.
            # Bonus for high-value types (Security, Performance, Boundary, etc.)
            types_present = set(tc.get("test_type", "") for tc in test_cases)
            base_diversity = min((len(types_present) / 10.0) * 100, 100.0)
            high_value_bonus = min(len(types_present & HIGH_VALUE_TYPES) * 5, 25)
            diversity_score = min(base_diversity + high_value_bonus, 100.0)

            # ── 3. Bug risk inverse score (0-100) ────────────────────────────
            # Lower bug risk → higher score
            bug_risk_score = 100.0 - min(max(avg_bug_risk, 0.0), 100.0)

            # ── 4. Security coverage (0-100) ──────────────────────────────────
            # Full score at 6+ security test cases
            security_tcs = [tc for tc in test_cases if tc.get("test_type") == "Security"]
            security_score = min((len(security_tcs) / 6.0) * 100, 100.0)

            # ── 5. Performance coverage (0-100) ───────────────────────────────
            # Full score at 4+ performance test cases
            perf_tcs = [tc for tc in test_cases if tc.get("test_type") == "Performance"]
            perf_score = min((len(perf_tcs) / 4.0) * 100, 100.0)

            # ── 6. PRD Quality score (0-100) ──────────────────────────────────
            # A richer PRD (more chunks) = better quality.
            # Full score at 20+ indexed chunks; baseline 50 if no chunks available.
            prd_quality_score = (
                min((prd_chunk_count / 20.0) * 100, 100.0)
                if prd_chunk_count > 0
                else 50.0
            )

            # ── Final weighted score (deterministic) ──────────────────────────
            final_score = (
                cov_score         * self.weights["coverage"] +
                trace_score       * self.weights["traceability"] +
                diversity_score   * self.weights["diversity"] +
                bug_risk_score    * self.weights["bug_risk"] +
                security_score    * self.weights["security"] +
                perf_score        * self.weights["performance"] +
                prd_quality_score * self.weights["prd_quality"]
            )
            final_score = round(min(final_score, 100.0), 1)

            # ── Grade ─────────────────────────────────────────────────────────
            grade = "D"
            if final_score >= 90:    grade = "A+"
            elif final_score >= 80:  grade = "A"
            elif final_score >= 70:  grade = "B"
            elif final_score >= 60:  grade = "C"

            result = {
                "total_score": final_score,
                "grade": grade,
                "breakdown": {
                    "coverage_points":     round(cov_score * self.weights["coverage"], 1),
                    "traceability_points": round(trace_score * self.weights["traceability"], 1),
                    "diversity_points":    round(diversity_score * self.weights["diversity"], 1),
                    "bug_risk_points":     round(bug_risk_score * self.weights["bug_risk"], 1),
                    "security_points":     round(security_score * self.weights["security"], 1),
                    "performance_points":  round(perf_score * self.weights["performance"], 1),
                    "prd_quality_points":  round(prd_quality_score * self.weights["prd_quality"], 1),
                },
                "raw_metrics": {
                    "coverage_pct":           round(coverage_percentage, 1),
                    "avg_bug_risk":           round(avg_bug_risk, 1),
                    "complexity":             round(complexity_score, 1),
                    "test_types_covered":     len(types_present),
                    "total_test_cases":       len(test_cases),
                    "security_test_cases":    len(security_tcs),
                    "performance_test_cases": len(perf_tcs),
                    "prd_chunk_count":        prd_chunk_count,
                    "types_present":          sorted(list(types_present)),
                },
            }
            logger.info(
                f"QA Intelligence Score: {final_score} ({grade}) | "
                f"Cov={cov_score:.1f}% Div={diversity_score:.1f}% "
                f"Sec={security_score:.1f}% Perf={perf_score:.1f}% "
                f"BugRisk={bug_risk_score:.1f}% PRDQuality={prd_quality_score:.1f}%"
            )
            return result

        except Exception as e:
            logger.error(f"Error calculating QA Intelligence Score: {e}", exc_info=True)
            return {"total_score": 0, "grade": "F", "breakdown": {}, "raw_metrics": {}, "error": str(e)}

    def generate_insights(self, score_dict: Dict[str, Any]) -> List[str]:
        """Generates human-readable improvement insights from the score breakdown."""
        insights = []
        b = score_dict.get("breakdown", {})
        m = score_dict.get("raw_metrics", {})
        score = score_dict.get("total_score", 0)

        if score >= 80:
            insights.append(f"🌟 **Excellent QA Suite** (Grade: {score_dict.get('grade', 'A')}): This is a thorough, industry-grade test plan.")
        elif score >= 60:
            insights.append(f"✅ **Good Coverage** (Grade: {score_dict.get('grade', 'B')}): Suite is solid. Expand edge case and security tests for A-grade.")
        else:
            insights.append(f"⚠️ **Needs Improvement** (Grade: {score_dict.get('grade', 'D')}): Run the pipeline with a detailed PRD to improve scores.")

        if b.get("coverage_points", 0) < (self.weights["coverage"] * 100 * 0.6):
            insights.append("📉 **Low PRD Coverage**: Add more Functional and Integration tests targeting specific PRD sections.")

        if b.get("security_points", 0) < (self.weights["security"] * 100 * 0.5):
            sec_count = m.get("security_test_cases", 0)
            insights.append(f"🔒 **Security Gap**: Only {sec_count} security test(s) found. Target 6+ (SQL injection, XSS, brute force, token attacks).")

        if b.get("performance_points", 0) < (self.weights["performance"] * 100 * 0.5):
            perf_count = m.get("performance_test_cases", 0)
            insights.append(f"⚡ **Performance Gap**: Only {perf_count} performance test(s). Add load/stress/concurrent user tests (target 4+).")

        if b.get("prd_quality_points", 0) < (self.weights["prd_quality"] * 100 * 0.5):
            chunks = m.get("prd_chunk_count", 0)
            insights.append(f"📄 **PRD Quality**: Only {chunks} PRD chunks indexed. A richer, more detailed PRD produces better AI test generation.")

        if b.get("diversity_points", 0) < (self.weights["diversity"] * 100 * 0.7):
            types = m.get("types_present", [])
            missing = sorted(ALL_TESTING_TYPES - set(types))
            if missing:
                insights.append(f"🧩 **Low Test Diversity**: Missing test types: {', '.join(missing)}. Add these to maximize score.")

        if not insights:
            insights.append("💡 All scoring dimensions look healthy. Continue maintaining test variety.")

        return insights
