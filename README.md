# 🤖 Intelligent QA Automation Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, deterministic AI QA Automation Platform that autonomously ingests Product Requirements Documents (PRDs) and instantly generates comprehensive, production-ready test suites using state-of-the-art LLMs. 

Designed for high accuracy, speed, and real-world software testing coverage.

---

## 🚀 Features

- **Document Understanding (RAG)**: Automatically chunks, embeds (using `all-MiniLM-L6-v2`), and semantically searches large PRD PDFs to extract core testable requirements (must, shall, should).
- **Ultra-Fast Deterministic Generation**: Runs a highly optimized prompting pipeline via Groq (Llama 3 8B) or local Ollama to bypass multi-agent overhead, generating 60-120+ high-quality test cases in seconds.
- **Deep Test Coverage**: Generates cross-functional tests automatically, spanning:
  - Functional & UI
  - Security & Injection (SQLi, XSS)
  - Edge Cases & Boundary Conditions
  - Integration & Performance
- **Smart Deduplication**: Utilizes cosine similarity clustering to combine overlapping requirements, ensuring lean, non-redundant test suites.
- **Priority & Bug Risk Scoring**: Leverages a trained Random Forest Random Forest Machine Learning model (`models/random_forest_model.pkl`) to analyze historical requirement complexities and assign accurate Priority (P0-P3) and Severity ratings.
- **Rich Analytics Dashboard**: Includes interactive Plotly heat maps and radar charts correlating requirement IDs to test scenarios to visualize test depth.
- **Export Anywhere**: One-click download of test suites into standard QA formats:
  - Enterprise Excel QA Template (Color-coded)
  - Standard TestRail CSV (10 column standard)
  - Katalon Automation CSV

---

## 🏗️ Architecture

![Architecture](https://img.shields.io/badge/Architecture-RAG_%2B_LLM-purple)

1. **Document Processor**: Extracts text, breaks by headings, isolating declarative logic.
2. **Vector Store**: Uses FAISS for high-speed nearest-neighbor retrieval of requirement context.
3. **Test Generator**: Iterates in optimized batches, pinging Groq API or Local LLM.
4. **Coverage Analyzer / ML Model**: Predicts bug risks, calculates complexity, and maps requirement IDs back to generated tests to guarantee >80% PRD coverage.
5. **Streamlit UI**: A beautiful, dark-mode reactive frontend that shows live generation progress.

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Sasritha7832/Ai-Automated-test-case-generation.git
   cd Ai-Automated-test-case-generation
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Set up your LLM Backend (Choose A or B):**
   
   **Option A: Cloud (Lightning Fast - Recommended)**
   Create a `.env` file in the root directory and add a free Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_api_key_here
   ```

   **Option B: Local (Private, No API limits)**
   Install [Ollama](https://ollama.com/) and download the models:
   ```bash
   ollama pull llama3:8b
   ollama pull gemma3:4b
   ```

4. **Launch the platform:**
   ```bash
   python -m streamlit run ui_app.py
   ```

---

## 🧪 Testing it out

We have provided three realistic, highly complex sample PRDs to test the engine's extraction capabilities:
- `sample_prds/Healthcare_Portal_PRD.pdf` (Strict security & HIPPA logic)
- `sample_prds/FinTech_Payment_App_PRD.pdf` (Transactions & third-party integrations)
- `sample_prds/Enterprise_GlobalTrade_Brokerage_PRD.pdf` (Massive, dense, enterprise scale)

*(If you don't see them, generate them by running `python generate_enterprise_prd.py` and `python generate_sample_prds.py`)*

---

## 🛠️ Built With
- **[Streamlit](https://streamlit.io/)** - Frontend UI
- **[LangChain](https://langchain.com/)** - Document parsing & chunking
- **[FAISS](https://faiss.ai/)** - Local Vector Database
- **[Sentence-Transformers](https://sbert.net/)** - Local Embedding Model 
- **[Scikit-Learn](https://scikit-learn.org/)** - ML Bug Risk Prediction
- **[Ollama](https://ollama.com/) / [Groq](https://groq.com/)** - Core inference engine
