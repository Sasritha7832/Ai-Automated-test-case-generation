import os
os.environ["OPENAI_API_KEY"] = "NA"
import sys
import unittest
from unittest.mock import patch, MagicMock

# Import app modules
from autonomous_qa_runner import AutonomousQARunner

class MockDocument:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}

class DummyUploadedFile:
    def getvalue(self):
        return b"dummy pdf content"

class TestQAPipeline(unittest.TestCase):
    @patch('document_processor.PyPDFLoader')
    def test_full_autonomous_pipeline(self, MockLoader):
        print("Starting E2E Pipeline Test...")
        # Setup mock loader to return a dummy document
        mock_instance = MockLoader.return_value
        mock_instance.load.return_value = [
            MockDocument(page_content="The system must have an Authentication module. Users require a secure login portal where they input their email and password. Passwords must be 8 characters long, containing numbers and special characters. Admin users should be routed to a dashboard, while standard users go to the homepage. The system should handle 10,000 concurrent login requests (performance constraint).")
        ]

        runner = AutonomousQARunner(vector_store=None)
        dummy_file = DummyUploadedFile()
        
        # Run report
        report = runner.run_full_pipeline(dummy_file, "Authentication")
        
        # Validate
        self.assertEqual(report["status"], "success", f"Pipeline failed: {report.get('errors')}")
        self.assertTrue(len(report["test_cases"]) > 0, "No test cases generated.")
        
        # Check new Schema structure mapping
        first_tc = report["test_cases"][0]
        print(f"DEBUG: first_tc keys = {first_tc.keys()}")
        self.assertIn("module", first_tc)
        self.assertIn("test_type", first_tc)
        self.assertIn("title", first_tc)
        self.assertIn("steps", first_tc)
        
        print(f"✅ Pipeline executed successfully in {report['timing'].get('total_time')}s")
        print(f"📊 Generated {len(report['test_cases'])} tests across {len(set([tc.get('test_type') for tc in report['test_cases']]))} categories.")

if __name__ == '__main__':
    unittest.main()
