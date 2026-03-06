"""
bug_report_generator.py
------------------------
Generates structured bug report templates for failed or at-risk test cases.

Provides:
  - BugReportGenerator.generate_report(...)  → dict
  - BugReportGenerator.to_markdown(report)  → str
  - BugReportGenerator.to_csv_bytes(reports) → bytes
"""

import io
import csv
import datetime
from typing import List, Dict, Any
from logger import get_logger

logger = get_logger("BugReportGenerator")

_SEVERITY_PRIORITY_MAP = {
    "Critical": "P0",
    "High":     "P1",
    "Medium":   "P2",
    "Low":      "P3",
}

_BUG_ID_COUNTER = 0  # module-level counter (resets on app restart)


def _next_bug_id() -> str:
    global _BUG_ID_COUNTER
    _BUG_ID_COUNTER += 1
    return f"BUG-{_BUG_ID_COUNTER:04d}"


class BugReportGenerator:
    """
    Generates structured bug reports from failed or at-risk test cases.
    Reports follow a standard QA defect reporting template.
    """

    def generate_report(
        self,
        test_case: Dict[str, Any],
        actual_result: str = "",
        severity: str = "Medium",
        reporter: str = "AI QA System",
        environment: str = "Test / QA Environment",
        os_browser: str = "Chrome 120 / Windows 11",
    ) -> Dict[str, Any]:
        """
        Generate a structured bug report dict from a failed test case.

        Args:
            test_case:     The test case dict (must have test_case_id, scenario/title, module, test_type, steps).
            actual_result: What actually happened during execution.
            severity:      Bug severity — Critical / High / Medium / Low.
            reporter:      Who found the bug.
            environment:   Test environment description.
            os_browser:    OS and browser specification.

        Returns:
            Structured bug report dict.
        """
        # Normalize fields
        tc_id    = test_case.get("test_case_id", "TC???")
        title    = test_case.get("scenario", test_case.get("title", "Untitled Test Case"))
        module   = test_case.get("module", "General")
        ttype    = test_case.get("test_type", "Functional")
        priority = _SEVERITY_PRIORITY_MAP.get(severity, "P2")

        # Extract steps
        steps_raw = test_case.get("steps", test_case.get("test_steps", []))
        steps_text_parts = []
        if isinstance(steps_raw, list):
            for i, s in enumerate(steps_raw, 1):
                if isinstance(s, dict):
                    steps_text_parts.append(f"{i}. {s.get('description', str(s))}")
                else:
                    steps_text_parts.append(f"{i}. {s}")
        elif isinstance(steps_raw, str):
            steps_text_parts = [steps_raw]
        steps_to_reproduce = "\n".join(steps_text_parts) if steps_text_parts else "See test case steps."

        expected = test_case.get("expected_result", "")
        preconditions = test_case.get("preconditions", "")

        bug_id = _next_bug_id()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = {
            "bug_id":            bug_id,
            "title":             f"[{module}] {title}",
            "related_tc_id":     tc_id,
            "module":            module,
            "test_type":         ttype,
            "severity":          severity,
            "priority":          priority,
            "status":            "Open",
            "reporter":          reporter,
            "assignee":          "Unassigned",
            "environment":       environment,
            "os_browser":        os_browser,
            "date_reported":     timestamp,
            "preconditions":     preconditions,
            "steps_to_reproduce": steps_to_reproduce,
            "expected_result":   expected,
            "actual_result":     actual_result or "Test execution failed — see logs.",
            "attachments":       [],
            "notes":             f"Auto-generated from test case {tc_id} ({ttype})",
        }
        logger.info(f"Bug report generated: {bug_id} for TC {tc_id}")
        return report

    def to_markdown(self, report: Dict[str, Any]) -> str:
        """Converts a bug report dict to a formatted Markdown string."""
        md = f"""# 🐛 Bug Report: {report['bug_id']}

**Title:** {report['title']}  
**Related TC:** `{report['related_tc_id']}`  
**Module:** {report['module']}  
**Test Type:** {report['test_type']}  
**Severity:** {report['severity']} | **Priority:** {report['priority']}  
**Status:** {report['status']}  
**Reporter:** {report['reporter']} | **Assignee:** {report['assignee']}  
**Environment:** {report['environment']}  
**OS / Browser:** {report['os_browser']}  
**Date Reported:** {report['date_reported']}  

---

## Preconditions
{report['preconditions'] or 'None specified'}

## Steps to Reproduce
{report['steps_to_reproduce']}

## Expected Result
{report['expected_result'] or 'See test case expected result.'}

## Actual Result
{report['actual_result']}

---
*{report['notes']}*
"""
        return md

    def to_csv_bytes(self, reports: List[Dict[str, Any]]) -> bytes:
        """Exports a list of bug reports to CSV bytes (Jira-compatible)."""
        if not reports:
            return b""

        fieldnames = [
            "bug_id", "title", "related_tc_id", "module", "test_type",
            "severity", "priority", "status", "reporter", "assignee",
            "environment", "os_browser", "date_reported",
            "preconditions", "steps_to_reproduce", "expected_result", "actual_result", "notes",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(reports)
        data = buf.getvalue().encode("utf-8")
        logger.info(f"Bug report CSV export: {len(reports)} reports, {len(data):,} bytes.")
        return data
