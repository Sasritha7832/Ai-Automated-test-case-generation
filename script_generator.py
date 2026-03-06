import os
from typing import List, Dict, Any
from logger import get_logger

logger = get_logger("ScriptGenerator")

class ScriptGenerator:
    """
    Translates JSON-formatted structured test cases into executable test scripts.
    Supports basic scaffolds for Pytest, Playwright, and Selenium.
    """
    
    def __init__(self):
        self.supported_frameworks = ["pytest", "playwright", "selenium"]

    def generate_script(self, test_cases: List[Dict[str, Any]], framework: str = "pytest") -> str:
        """
        Generates Python test automation code based on the generated test cases.
        """
        framework = framework.lower()
        if framework not in self.supported_frameworks:
            logger.error(f"Unsupported framework: {framework}")
            return f"# Framework '{framework}' is not currently supported."

        if framework == "pytest":
            return self._generate_pytest_script(test_cases)
        elif framework == "playwright":
            return self._generate_playwright_script(test_cases)
        elif framework == "selenium":
            return self._generate_selenium_script(test_cases)
            
        return ""

    def _generate_pytest_script(self, test_cases: List[Dict[str, Any]]) -> str:
        script_lines = [
            "import pytest",
            "import requests",
            "",
            "BASE_URL = 'http://localhost:8000/api'",
            ""
        ]
        
        for i, tc in enumerate(test_cases):
            tc_id = tc.get("id", f"tc_{i+1}")
            desc = tc.get("description", "No description provided").replace("'", "\\'")
            steps = tc.get("steps", [])
            expected = tc.get("expected_result", "No expected result provided").replace("'", "\\'")
            
            # Format function name
            func_name = f"test_{tc_id.lower().replace(' ', '_').replace('-', '_')}"
            
            script_lines.append(f"def {func_name}():")
            script_lines.append(f"    \"\"\"")
            script_lines.append(f"    Description: {desc}")
            script_lines.append(f"    Expected: {expected}")
            script_lines.append(f"    \"\"\"")
            
            if not steps:
                script_lines.append("    # TODO: Implement test steps")
                script_lines.append("    pass\n")
                continue
                
            for step in steps:
                step_text = str(step).replace('"', '\\"')
                script_lines.append(f"    # Step: {step_text}")
                
            # Generic assertion scaffold
            script_lines.append(f"    # assert result == expected_result")
            script_lines.append("    pass\n")
            
        return "\n".join(script_lines)

    def _generate_playwright_script(self, test_cases: List[Dict[str, Any]]) -> str:
        script_lines = [
            "import pytest",
            "from playwright.sync_api import Page, expect",
            "",
            "BASE_URL = 'http://localhost:3000'",
            ""
        ]
        
        # Only process UI relevant test cases or just scaffold all
        for i, tc in enumerate(test_cases):
            cat = tc.get("category", "")
            if "UI" not in cat and "Frontend" not in cat and len(test_cases) > 5:
                continue # Skip non-UI tests if there are many tests and this is playwright
                
            tc_id = tc.get("id", f"tc_{i+1}")
            desc = tc.get("description", "No description provided").replace("'", "\\'")
            steps = tc.get("steps", [])
            
            func_name = f"test_ui_{tc_id.lower().replace(' ', '_').replace('-', '_')}"
            
            script_lines.append(f"def {func_name}(page: Page):")
            script_lines.append(f"    \"\"\" {desc} \"\"\"")
            script_lines.append(f"    page.goto(BASE_URL)")
            
            for step in steps:
                step_text = str(step)
                script_lines.append(f"    # {step_text}")
                # Try to guess some playwright commands based on keywords
                lower_step = step_text.lower()
                if "click" in lower_step:
                    script_lines.append(f"    # page.locator('text=\"something\"').click()")
                elif "enter" in lower_step or "type" in lower_step or "input" in lower_step:
                    script_lines.append(f"    # page.locator('input[name=\"field\"]').fill('value')")
                    
            script_lines.append("    # expect(page).to_have_title(re.compile(r'.*'))")
            script_lines.append("    pass\n")
            
        if len(script_lines) == 5:
             script_lines.append("# No UI specific test cases found to generate Playwright scripts for.")
             
        return "\n".join(script_lines)

    def _generate_selenium_script(self, test_cases: List[Dict[str, Any]]) -> str:
        script_lines = [
            "import pytest",
            "from selenium import webdriver",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait",
            "from selenium.webdriver.support import expected_conditions as EC",
            "",
            "@pytest.fixture",
            "def driver():",
            "    driver = webdriver.Chrome()",
            "    driver.implicitly_wait(10)",
            "    yield driver",
            "    driver.quit()",
            ""
        ]
        
        for i, tc in enumerate(test_cases):
             # Similar filtering or generation
            tc_id = tc.get("id", f"tc_{i+1}")
            desc = tc.get("description", "").replace("'", "\\'")
            
            func_name = f"test_sel_{tc_id.lower().replace(' ', '_').replace('-', '_')}"
            
            script_lines.append(f"def {func_name}(driver):")
            script_lines.append(f"    \"\"\" {desc} \"\"\"")
            script_lines.append(f"    driver.get('http://localhost:3000')")
            
            for step in tc.get("steps", []):
                script_lines.append(f"    # Step: {step}")
                
            script_lines.append("    # element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'myElement')))")
            script_lines.append("    # assert element.is_displayed()")
            script_lines.append("    pass\n")
            
        return "\n".join(script_lines)
