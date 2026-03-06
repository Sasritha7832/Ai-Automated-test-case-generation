"""
Direct runner test — runs WITHOUT unittest framework to bypass output truncation.
"""
import sys
sys.path.insert(0, '.')

from unittest.mock import patch

class MockDocument:
    def __init__(self, page_content):
        self.page_content = page_content
        self.metadata = {}

class DummyFile:
    def getvalue(self):
        return b"dummy pdf content"

from autonomous_qa_runner import AutonomousQARunner

with patch('document_processor.PyPDFLoader') as MockLoader:
    mock_instance = MockLoader.return_value
    mock_instance.load.return_value = [
        MockDocument("The Authentication module handles login for email and password. Users receive a JWT on success. Passwords expire every 90 days. The system supports 10000 concurrent sessions.")
    ]

    runner = AutonomousQARunner()
    report = runner.run_full_pipeline(DummyFile(), "Authentication")

print("\n" + "="*60)
print(f"STATUS : {report['status']}")
print(f"ERRORS : {report['errors']}")
print(f"TEST CASES: {len(report['test_cases'])}")
print(f"TIMING : {report['timing']}")
