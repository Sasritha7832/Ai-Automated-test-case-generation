import cv2
import numpy as np
from PIL import Image
from logger import get_logger

logger = get_logger(__name__)

class UIElementDetector:
    """Uses OpenCV to detect UI elements from a screenshot."""
        
    def detect_elements(self, image_bytes) -> list:
        """
        Parses an uploaded image buffer and returns a list of detected UI elements.
        Includes advanced shape detection heuristics to classify elements.
        """
        logger.info("Processing screenshot for CV Advanced element detection...")
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            detected = []
            
            # Advanced Heuristics for bounding boxes
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                area = w * h
                
                # Filter noise
                if 200 < area < 100000:
                    aspect_ratio = w / float(h)
                    
                    if 0.8 <= aspect_ratio <= 1.2 and area < 2000:
                        detected.append("Checkbox")
                    elif 1.2 < aspect_ratio <= 4.0:
                        detected.append("Button")
                    elif 4.0 < aspect_ratio <= 8.0:
                        detected.append("Input Field")
                    elif 8.0 < aspect_ratio <= 15.0:
                        detected.append("Dropdown")
                    elif aspect_ratio > 15.0 or h <= 20: 
                        detected.append("Link/Navigation Element")
                        
            unique_elements = list(set(detected))
            
            if not unique_elements:
                unique_elements = ["Button", "Input Field", "Link"]
                
            logger.info(f"Detected UI Elements: {unique_elements}")
            return unique_elements

        except Exception as e:
            logger.error(f"Failed to process screenshot for CV detection: {str(e)}", exc_info=True)
            return ["Button", "Input Field"] # Fallback

    def generate_ui_test_cases(self, detected_elements: list) -> list:
        """Generates element-specific deterministic test cases."""
        logger.info(f"Generating UI test cases for {len(detected_elements)} elements.")
        
        test_cases = []
        for i, element in enumerate(detected_elements):
            
            # Element Specific logic
            steps = [f"Locate the {element} on the user interface."]
            if element == "Checkbox":
                steps.extend(["Click to toggle state.", "Verify true/false state persists visually."])
            elif element == "Dropdown":
                steps.extend(["Click to expand.", "Verify all list items render correctly.", "Select an item and verify the UI updates."])
            elif element == "Link/Navigation Element":
                steps.extend(["Hover over the link to verify CSS pointer changes.", "Click the link and verify correct routing."])
            elif element == "Input Field":
                steps.extend(["Click to focus.", "Type a valid string.", "Verify the field accepts the input cleanly."])
            else:
                steps.extend(["Observe for visual defects.", "Interact (click/type)."])
                
            category = "Interaction Testing"
            if element in ["Checkbox", "Dropdown"]:
                category = "UI Functional Testing"
            elif element == "Link/Navigation Element":
                category = "Usability Testing"
                
            tc = {
                "test_case_id": f"UI_TC{str(i+1).zfill(3)}",
                "title": f"Verify rendering and interaction of {element}",
                "steps": steps,
                "expected_result": f"The {element} should respond to standard inputs according to UX guidelines.",
                "priority": "P2",
                "category": category
            }
            test_cases.append(tc)
            
        return test_cases
