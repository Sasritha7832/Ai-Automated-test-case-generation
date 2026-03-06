"""
document_processor.py
---------------------
Requirement-aware PRD processor.

Improvements over the original random-chunking approach:
1. Splits the PDF by headings (#/##/### or numbered sections)
2. Extracts sentences containing requirement signals (must/shall/should/allow/etc.)
3. Each extracted requirement becomes its own chunk with rich metadata:
   - module       (derived from section title)
   - section_title
   - requirement_text
4. Falls back to full-text chunking if < 5 requirements found
"""

import re
import tempfile
import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document
from config import Config
from logger import get_logger

logger = get_logger(__name__)

# ── Requirement signal words ──────────────────────────────────────────────────
REQUIREMENT_SIGNALS = re.compile(
    r'\b(must|shall|should|allow|enable|validate|process|authenticate|'
    r'create|update|delete|verify|ensure|support|provide|restrict|enforce|'
    r'require|handle|manage|display|generate|calculate|send|receive|store|'
    r'encrypt|authorize|reject|respond|notify|track|log|report)\b',
    re.IGNORECASE,
)

# Heading patterns: markdown headings or numbered sections
HEADING_PATTERN = re.compile(
    r'^(#{1,4}\s+.+|(?:\d+\.)+\s+.+)$',
    re.MULTILINE,
)

# Fallback text splitter (used if not enough requirements extracted)
_FALLBACK_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=Config.CHUNK_SIZE,
    chunk_overlap=Config.CHUNK_OVERLAP,
)


def _clean_heading(heading: str) -> str:
    """Strip markdown # markers and numbering from a heading string."""
    cleaned = re.sub(r'^#+\s*', '', heading)         # remove # markers
    cleaned = re.sub(r'^(?:\d+\.)+\s*', '', cleaned)  # remove 1.2.3 numbering
    return cleaned.strip()


def _extract_sections(full_text: str) -> List[dict]:
    """
    Split full PRD text into sections by heading.
    Returns list of {"title": str, "content": str}.
    """
    sections = []
    lines = full_text.split('\n')

    current_title = "Introduction"
    current_lines = []

    for line in lines:
        if HEADING_PATTERN.match(line.strip()):
            # Save the previous section
            if current_lines:
                sections.append({
                    "title": current_title,
                    "content": '\n'.join(current_lines).strip(),
                })
            current_title = _clean_heading(line.strip())
            current_lines = []
        else:
            current_lines.append(line)

    # Save the last section
    if current_lines:
        sections.append({
            "title": current_title,
            "content": '\n'.join(current_lines).strip(),
        })

    return [s for s in sections if s["content"].strip()]


def _extract_requirements(section_title: str, content: str) -> List[dict]:
    """
    Extract individual requirement sentences from a section's content.
    A sentence is a requirement if it contains at least one requirement signal word.
    Returns list of {"requirement_text": str, "section_title": str, "module": str}.
    """
    # Split content into sentences (on . ! ? or newlines)
    raw_sentences = re.split(r'(?<=[.!?])\s+|\n', content)
    requirements = []

    for sent in raw_sentences:
        sent = sent.strip()
        if len(sent) < 20:       # skip very short strings (noise)
            continue
        if REQUIREMENT_SIGNALS.search(sent):
            requirements.append({
                "requirement_text": sent,
                "section_title": section_title,
                "module": section_title,
            })

    return requirements


def process_prd_document(uploaded_file) -> List[Document]:
    """
    Parses a PRD PDF and returns requirement-aware Document chunks.

    Each chunk represents one extracted requirement sentence with metadata:
        {"module": str, "section_title": str, "requirement_text": str}

    Falls back to standard text chunking if < 5 requirements are found.
    """
    logger.info("Starting requirement-aware PRD processing...")

    try:
        # ── Save & load PDF ──────────────────────────────────────────────────
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        logger.info(f"Loading PDF from: {tmp_path}")
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        logger.info(f"Loaded {len(pages)} pages.")

        full_text = "\n".join(p.page_content for p in pages)

        # ── Extract sections ──────────────────────────────────────────────────
        sections = _extract_sections(full_text)
        logger.info(f"Found {len(sections)} sections in PRD.")

        # ── Extract requirements from each section ───────────────────────────
        all_requirements = []
        for section in sections:
            reqs = _extract_requirements(section["title"], section["content"])
            all_requirements.extend(reqs)

        logger.info(f"Extracted {len(all_requirements)} requirement sentences.")

        # ── Build Documents from requirements ─────────────────────────────────
        if len(all_requirements) >= 5:
            documents = []
            for req in all_requirements:
                doc = Document(
                    page_content=req["requirement_text"],
                    metadata={
                        "module": req["module"],
                        "section_title": req["section_title"],
                        "requirement_text": req["requirement_text"],
                    },
                )
                documents.append(doc)
            logger.info(
                f"Requirement-aware mode: {len(documents)} requirement documents created."
            )

        else:
            # ── Fallback: standard recursive chunking ─────────────────────────
            logger.warning(
                f"Only {len(all_requirements)} requirements found — "
                "falling back to standard chunking."
            )
            splitter = _FALLBACK_SPLITTER
            sections_for_fallback = sections if sections else [{"title": "General", "content": full_text}]
            documents = []
            for section in sections_for_fallback:
                if section["content"].strip():
                    chunk_docs = splitter.create_documents(
                        [section["content"]],
                        metadatas=[{
                            "module": section["title"],
                            "section_title": section["title"],
                            "requirement_text": section["content"][:200],
                        }],
                    )
                    documents.extend(chunk_docs)

            if not documents:
                documents = splitter.create_documents(
                    [full_text],
                    metadatas=[{"module": "General", "section_title": "General", "requirement_text": ""}],
                )

            logger.info(f"Fallback chunking: {len(documents)} chunks created.")

        os.unlink(tmp_path)
        return documents

    except Exception as e:
        logger.error(f"Failed to process PRD document: {e}", exc_info=True)
        raise


def get_requirements_from_documents(documents: List[Document]) -> List[dict]:
    """
    Extract structured requirement list from processed Documents.
    Returns list of dicts with: requirement_text, section_title, module.
    Useful for passing to TestGenerator.generate_tests().
    """
    requirements = []
    seen = set()

    for doc in documents:
        text = doc.page_content.strip()
        if not text or text in seen:
            continue
        seen.add(text)

        requirements.append({
            "requirement_text": doc.metadata.get("requirement_text", text),
            "section_title": doc.metadata.get("section_title", "General"),
            "module": doc.metadata.get("module", "General"),
        })

    return requirements