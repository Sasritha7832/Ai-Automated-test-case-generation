import os
import pandas as pd
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from config import Config
from logger import get_logger

logger = get_logger(__name__)

def generate_synthetic_dataset(path: str):
    """Generates a synthetic dataset for bug risk prediction if one doesn't exist."""
    logger.info("Generating synthetic requirements dataset...")
    
    data = [
        {"Requirement Text": "User must be able to log in with email and password", "Module": "Authentication", "Complexity": "Low", "Bug Count": 1, "Risk Label": "Low"},
        {"Requirement Text": "System must process transactions concurrently from 10,000 users", "Module": "Payments", "Complexity": "High", "Bug Count": 8, "Risk Label": "High"},
        {"Requirement Text": "Admin dashboard should display total sales for the month", "Module": "Reporting", "Complexity": "Medium", "Bug Count": 3, "Risk Label": "Medium"},
        {"Requirement Text": "Password reset link must expire after 15 minutes", "Module": "Authentication", "Complexity": "Medium", "Bug Count": 2, "Risk Label": "Low"},
        {"Requirement Text": "Integration with external REST API for real-time shipping quotes", "Module": "Shipping", "Complexity": "High", "Bug Count": 12, "Risk Label": "High"},
        {"Requirement Text": "Background worker to clean up soft-deleted records daily", "Module": "Database", "Complexity": "Medium", "Bug Count": 4, "Risk Label": "Medium"},
        {"Requirement Text": "Update profile picture and save to AWS S3 bucket", "Module": "User Profile", "Complexity": "Low", "Bug Count": 1, "Risk Label": "Low"},
        {"Requirement Text": "Compute complex tax regulations dynamically per state", "Module": "Checkout", "Complexity": "High", "Bug Count": 7, "Risk Label": "High"},
        {"Requirement Text": "Send an email notification when an order is dispatched", "Module": "Notifications", "Complexity": "Low", "Bug Count": 0, "Risk Label": "Low"},
        {"Requirement Text": "Real-time websocket connections for chat functionality", "Module": "Social", "Complexity": "High", "Bug Count": 9, "Risk Label": "High"},
        {"Requirement Text": "Add a new column to the customers table", "Module": "Database", "Complexity": "Low", "Bug Count": 1, "Risk Label": "Low"},
        {"Requirement Text": "OAuth2 SSO login with Google and Facebook", "Module": "Authentication", "Complexity": "High", "Bug Count": 6, "Risk Label": "High"},
    ]
    
    # Duplicate and add noise to create a decent sized dataset for simple training
    df = pd.DataFrame(data * 20)  # ~240 rows
    df.to_csv(path, index=False)
    logger.info(f"Saved dataset to {path} with {len(df)} rows.")

def train_model():
    logger.info("Starting ML model training pipeline...")
    
    if not os.path.exists(Config.DATASET_PATH):
        generate_synthetic_dataset(Config.DATASET_PATH)

    try:
        df = pd.read_csv(Config.DATASET_PATH)
        X = df["Requirement Text"]
        y = df["Risk Label"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Build pipeline: TF-IDF -> Random Forest
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', max_features=1000)),
            ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])

        logger.info("Training Random Forest Classifier on Requirement Text...")
        pipeline.fit(X_train, y_train)

        # Evaluate
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred)
        
        logger.info(f"Model Training Complete. Accuracy: {acc:.2f}")
        logger.info(f"Classification Report:\n{report}")

        # Save model
        joblib.dump(pipeline, Config.ML_MODEL_PATH)
        logger.info(f"Model successfully saved at {Config.ML_MODEL_PATH}")
        
    except Exception as e:
        logger.error(f"Error during ML pipeline training: {e}", exc_info=True)

if __name__ == "__main__":
    train_model()
