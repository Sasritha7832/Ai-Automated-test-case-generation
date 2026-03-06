import re
from logger import get_logger

logger = get_logger(__name__)

class ComplexityAnalyzer:
    """Scores requirement text complexity based on logic, depth, and entities."""
    
    CONDITIONAL_WORDS = {'if', 'when', 'unless', 'except', 'should', 'must', 'switch', 'case', 'else', 'otherwise'}
    WORKFLOW_WORDS = {'then', 'after', 'before', 'proceed', 'step', 'finally', 'next', 'previous'}
    API_DB_WORDS = {'database', 'api', 'server', 'request', 'response', 'query', 'auth', 'webhook', 'sync'}
    
    def analyze(self, text: str) -> dict:
        """
        Analyzes a chunk of requirement text and returns a dictionary with complexity score 
        and detected complexity factors.
        """
        if not text or not text.strip():
            return {"score": 0, "factors": ["Empty requirement"]}
            
        text_lower = text.lower()
        tokens = re.findall(r'\b\w+\b', text_lower)
        
        factors = []
        score = 0
        
        # 1. Base length complexity (longer texts tend to be more complex up to a limit)
        token_count = len(tokens)
        if token_count > 50:
            score += 20
            factors.append("High context volume (Token count > 50)")
        elif token_count > 20:
            score += 10
            
        # 2. Conditional Logic
        conditions_found = set(tokens).intersection(self.CONDITIONAL_WORDS)
        if len(conditions_found) > 0:
            score += min(len(conditions_found) * 10, 30)
            factors.append(f"Conditional Logic ({', '.join(list(conditions_found)[:3])})")
            
        # 3. Workflow Depth
        workflow_found = set(tokens).intersection(self.WORKFLOW_WORDS)
        if len(workflow_found) > 0:
            score += min(len(workflow_found) * 10, 25)
            factors.append("Multi-step Workflow Logic")
            
        # 4. API / Backend / Database Architecture
        tech_found = set(tokens).intersection(self.API_DB_WORDS)
        if len(tech_found) > 0:
            score += 25
            factors.append("Backend/Infrastructure dependency")
            
        # Normalize score to 100 max
        score = min(score, 100)
        
        # If very simple
        if score < 20 and not factors:
            factors.append("Simple straightforward requirement")
            
        logger.info(f"Requirement complexity assessed at {score}/100")
        
        return {
            "score": score,
            "factors": factors,
            "token_count": token_count
        }
