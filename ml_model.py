import joblib
import pandas as pd
from logger import get_logger
from config import Config
import os

logger = get_logger(__name__)

class RiskPredictor:
    """Handles inference for Bug Risk Prediction."""
    def __init__(self):
        self.model_path = Config.ML_MODEL_PATH
        self.pipeline = None
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                logger.info(f"Loaded ML model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}")
        else:
            logger.warning(f"ML model not found at {self.model_path}. Please train it first.")

    def predict_risk(self, requirement_text: str) -> dict:
        """
        Predicts the bug risk for a given requirement text.
        Returns a dictionary with 'risk_label' and 'confidence'.
        """
        if not self.pipeline:
            # Fallback if model isn't trained
            logger.warning("Predict called but pipeline is not loaded. Returning 'Unknown'")
            return {"risk_label": "Unknown", "confidence": 0.0}
        
        try:
            # Predict
            pred = self.pipeline.predict([requirement_text])[0]
            
            # Predict Probabilities
            probs = self.pipeline.predict_proba([requirement_text])[0]
            max_prob = max(probs)
            
            logger.info(f"Risk predicted: {pred} ({max_prob*100:.1f}%) for text: {requirement_text[:30]}...")
            
            return {
                "risk_label": pred,
                "confidence": round(max_prob * 100, 2)
            }
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return {"risk_label": "Error", "confidence": 0.0}
