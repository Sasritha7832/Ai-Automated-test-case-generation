"""
autonomous_qa_runner.py
-----------------------
Orchestrates the full QA pipeline end-to-end.

Refactored pipeline (CrewAI removed):
  PRD Upload
  → PRD Chunking (requirement-aware)
  → Vector Store (FAISS)
  → Requirement Extraction
  → Test Case Generation   ← TestGenerator (deterministic, single pass)
  → Deduplication
  → Priority Scoring
  → Coverage Analysis
  → Bug Risk Simulation
  → QA Intelligence Score
  → Analytics Dashboard

Removed:
  - CrewAI multi-agent kickoff
  - Retry loops (MAX_GENERATION_RETRIES)
  - Coverage recovery loops (per-requirement generation gives high coverage already)
"""

import time
from typing import Dict, Any, List

from rag_pipeline import RAGPipeline
from test_generator import TestGenerator
from document_processor import get_requirements_from_documents
from deduplication_engine import DeduplicationEngine
from priority_model import TestPriorityModel
from coverage_analyzer import CoverageAnalyzer
from bug_simulator import BugSimulator
from complexity_analyzer import ComplexityAnalyzer
from qa_intelligence_engine import QAIntelligenceEngine
from logger import get_logger

logger = get_logger("AutonomousQARunner")


class AutonomousQARunner:
    """
    Runs the entire QA pipeline automatically in one deterministic pass.
    Orchestrates ingestion, extraction, generation, analysis and scoring.
    """

    def __init__(self, vector_store=None, data_file_path: str = None):
        self.rag = RAGPipeline()
        self.generator = TestGenerator()
        self.dedup = DeduplicationEngine()
        self.priority = TestPriorityModel()
        self.coverage = CoverageAnalyzer()
        self.complexity = ComplexityAnalyzer()
        self.bug_sim = BugSimulator()
        self.qa_intel = QAIntelligenceEngine()
        logger.info("AutonomousQARunner initialized (deterministic pipeline).")

    def run_full_pipeline(self, pdf_file: Any, feature_name: str, progress_callback=None) -> Dict[str, Any]:
        """Run the entire pipeline and return a consolidated QA report."""
        report = {
            "status": "success",
            "feature_name": feature_name,
            "timing": {},
            "metrics": {},
            "test_cases": [],
            "coverage": {},
            "bug_risk": {},
            "intelligence_score": {},
            "errors": [],
        }

        start_time = time.time()

        try:
            # ── STEP 1: PRD ingestion → requirement-aware chunks + FAISS ─────
            t0 = time.time()
            logger.info("STEP 1: Ingesting PRD and building vector store...")
            if not self.rag.process_and_store(pdf_file):
                report["status"] = "failed"
                report["errors"].append("Failed to process and store PRD context.")
                return report
            report["timing"]["rag_processing"] = round(time.time() - t0, 2)

            # ── STEP 2: Retrieve RAG context + structured requirements ─────────
            t0 = time.time()
            logger.info(f"STEP 2: Extracting context for feature: {feature_name}")
            context = self.rag.retrieve_feature_context(feature_name)
            if not context:
                context = "No specific context found. Generate comprehensive tests."

            # Get structured requirement list from the processed documents
            all_texts = self.rag.vector_store.get_all_texts()
            prd_chunk_count = len(all_texts)
            requirements = get_requirements_from_documents(self.rag.get_documents())
            logger.info(f"STEP 2: {len(requirements)} structured requirements extracted.")
            report["timing"]["context_extraction"] = round(time.time() - t0, 2)

            # ── STEP 3: Complexity analysis ────────────────────────────────────
            t0 = time.time()
            logger.info("STEP 3: Complexity analysis...")
            comp_result = self.complexity.analyze(context)
            report["metrics"]["complexity"] = comp_result.get("score", 0)
            report["timing"]["complexity_analysis"] = round(time.time() - t0, 2)

            # ── STEP 4: Deterministic test case generation ─────────────────────
            t0 = time.time()
            logger.info("STEP 4: Generating test cases (deterministic, single pass)...")

            test_cases = self.generator.generate_tests(
                feature_name=feature_name,
                context=context,
                requirements=requirements if requirements else None,
                progress_callback=progress_callback
            )

            report["timing"]["test_generation"] = round(time.time() - t0, 2)

            if not test_cases:
                report["status"] = "failed"
                report["errors"].append("Test generation produced no test cases.")
                return report

            logger.info(f"STEP 4: Generated {len(test_cases)} test cases.")

            # ── STEP 5: Deduplication ──────────────────────────────────────────
            t0 = time.time()
            logger.info("STEP 5: Deduplicating...")
            dedup_result = self.dedup.deduplicate(test_cases)
            if isinstance(dedup_result, tuple):
                unique_tc, removed_count = dedup_result
            else:
                unique_tc = dedup_result
                removed_count = len(test_cases) - len(unique_tc)
            report["timing"]["deduplication"] = round(time.time() - t0, 2)
            report["metrics"]["duplicates_removed"] = removed_count
            logger.info(f"STEP 5: {removed_count} duplicates removed, {len(unique_tc)} unique retained.")

            # ── STEP 6: Priority Scoring ───────────────────────────────────────
            t0 = time.time()
            logger.info("STEP 6: Assigning priorities...")
            prioritized_tc = self.priority.assign_priorities(
                unique_tc,
                complexity_score=comp_result.get("score", 50),
                bug_risk_label="Medium",
            )
            report["timing"]["priority_scoring"] = round(time.time() - t0, 2)

            # ── STEP 7: Coverage Analysis ──────────────────────────────────────
            t0 = time.time()
            logger.info("STEP 7: Analyzing PRD semantic coverage...")

            # Build PRD sentences from requirement-aware chunks (better coverage)
            if requirements:
                prd_sentences = [r["requirement_text"] for r in requirements if r.get("requirement_text")]
            else:
                prd_sentences = []
                for chunk in all_texts:
                    prd_sentences.extend(
                        [s.strip() for s in chunk.split(".") if len(s.strip()) > 10]
                    )

            if prd_sentences:
                cov_result = self.coverage.analyze_coverage(prd_sentences, prioritized_tc)
            else:
                cov_result = {
                    "score": 0,
                    "covered": [],
                    "coverage_percentage": 0,
                    "missing": [],
                }

            coverage_pct = cov_result.get("coverage_percentage", cov_result.get("score", 0))
            report["timing"]["coverage_analysis"] = round(time.time() - t0, 2)
            logger.info(f"STEP 7: Coverage = {coverage_pct:.1f}%")

            report["test_cases"] = prioritized_tc
            report["coverage"] = cov_result
            report["metrics"]["total_test_cases"] = len(prioritized_tc)

            # ── STEP 8: Bug Risk Simulation ────────────────────────────────────
            t0 = time.time()
            logger.info("STEP 8: Bug risk simulation...")
            bug_scenarios = self.bug_sim.simulate_bugs(
                feature_name,
                comp_result.get("factors", []),
                context,
            )
            report["bug_risk"] = {"scenarios": bug_scenarios, "avg_risk": 50.0}
            report["timing"]["bug_simulation"] = round(time.time() - t0, 2)

            # ── STEP 9: QA Intelligence Score ──────────────────────────────────
            t0 = time.time()
            logger.info("STEP 9: Calculating QA Intelligence Score...")
            categories = len(set(tc.get("test_type", "") for tc in prioritized_tc))
            final_coverage_pct = cov_result.get("coverage_percentage", cov_result.get("score", 0))
            intel_score = self.qa_intel.calculate_score(
                coverage_percentage=final_coverage_pct,
                avg_bug_risk=50.0,
                complexity_score=comp_result.get("score", 0),
                test_categories=categories,
                test_cases=prioritized_tc,
                prd_chunk_count=prd_chunk_count,
            )
            report["intelligence_score"] = intel_score
            report["metrics"]["test_types_covered"] = categories
            report["insights"] = self.qa_intel.generate_insights(intel_score)
            report["timing"]["intelligence_scoring"] = round(time.time() - t0, 2)

            report["timing"]["total_time"] = round(time.time() - start_time, 2)
            logger.info(
                f"AutonomousQARunner completed in {report['timing']['total_time']}s. "
                f"Tests: {len(prioritized_tc)}, Coverage: {final_coverage_pct:.1f}%, "
                f"Score: {intel_score.get('total_score', 0)}/100"
            )
            return report

        except Exception as e:
            logger.error(f"Error in AutonomousQARunner: {e}", exc_info=True)
            report["status"] = "failed"
            report["errors"].append(str(e))
            return report
