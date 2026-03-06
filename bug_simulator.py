import random
from logger import get_logger

logger = get_logger(__name__)

class BugSimulator:
    """Rule-based + ML proxy engine to discover potential bug scenarios based on requirement text."""
    
    def simulate_bugs(self, requirement: str, complexity_factors: list, ml_risk_label: str) -> list:
        logger.info(f"Simulating bugs for requirement marked {ml_risk_label} risk...")
        
        req_lower = requirement.lower()
        bugs = []
        
        # 1. Database / State Scenarios
        if "database" in req_lower or "save" in req_lower or "update" in req_lower:
            bugs.append({
                "description": "Race condition when multiple users attempt to update the same record concurrently.",
                "affected_module": "Database / Concurrency",
                "risk_level": "High"
            })
            
        # 2. Authentication Scenarios
        if "login" in req_lower or "auth" in req_lower or "password" in req_lower:
            bugs.append({
                "description": "Session fixation vulnerability allowing token hijacking after password resets.",
                "affected_module": "Authentication / Security",
                "risk_level": "High"
            })
            bugs.append({
                "description": "Rate limiting not applied on failed login attempts, allowing brute force.",
                "affected_module": "Authentication / API",
                "risk_level": "Medium"
            })
            
        # 3. Notification / Email Scenarios
        if "email" in req_lower or "notify" in req_lower:
            bugs.append({
                "description": "SMTP timeout leading to unhandled exception and blocking the main user workflow.",
                "affected_module": "Notifications",
                "risk_level": "Medium"
            })
            
        # 4. Math / Performance Scenarios (Driven by ML / Complexity)
        if "Complex" in " ".join(complexity_factors) or ml_risk_label == "High":
            bugs.append({
                "description": "Memory leak detected under sustained load (10k+ requests) crashing the container.",
                "affected_module": "Infrastructure",
                "risk_level": "High"
            })
            
        if not bugs:
            # Fallback generic functional bug
            bugs.append({
                "description": "Null pointer exception on edge case inputs not explicitly handled in UI validation.",
                "affected_module": "Frontend Validation",
                "risk_level": "Low"
            })
            
        # Shuffle and limit to simulate variance
        random.shuffle(bugs)
        return bugs[:3] # Return top 3 plausible scenarios
