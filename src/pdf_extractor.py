"""
src/pdf_extractor.py
====================
Stage 2 — PDF Text Extraction

WHAT THIS MODULE DOES:
    Accepts a PDF file (as a path or bytes) and returns the raw text
    content from all pages.

WHY IT EXISTS:
    Before we can analyse a resume, we need to turn the binary PDF
    format into plain text. This module handles *only* that conversion.
    All the intelligence (name extraction, skill detection, etc.) lives
    in other modules.

LIBRARY USED:
    PyMuPDF (imported as "fitz") — fast, reliable, and handles most
    real-world PDF layouts well.

LIMITATIONS (Version 1):
    - Scanned PDFs (image-only) will produce little or no text.
      This is because the PDF contains a picture of text rather than
      actual text characters. OCR is NOT included in Version 1.
    - Password-protected PDFs are not supported.
    - Very complex multi-column layouts may produce text in the wrong order.
"""

import io
from pathlib import Path
from typing import Union

# PyMuPDF is installed as "PyMuPDF" but imported as "fitz"
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from src.utils import get_logger, clean_text

logger = get_logger(__name__)


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def extract_text_from_pdf(source: Union[str, Path, bytes]) -> str:
    """
    Extract all text from a PDF and return it as a single string.

    Parameters
    ----------
    source : str | Path | bytes
        - str or Path  → file path to a PDF on disk
        - bytes        → raw PDF bytes (e.g., from Streamlit's
                         st.file_uploader which returns a BytesIO/bytes)

    Returns
    -------
    str
        The extracted text. Returns an empty string if extraction
        fails for any reason — the caller should check for this.

    Notes
    -----
    We concatenate pages with two newlines between them so that
    section headings at the bottom of one page and content at the
    top of the next are not merged into a single token.
    """
    if not PYMUPDF_AVAILABLE:
        logger.error("PyMuPDF is not installed. Run: pip install PyMuPDF")
        return ""

    try:
        # Open the PDF from either a file path or raw bytes
        if isinstance(source, (str, Path)):
            doc = fitz.open(str(source))
        elif isinstance(source, (bytes, bytearray)):
            doc = fitz.open(stream=source, filetype="pdf")
        elif hasattr(source, "read"):
            # Streamlit UploadedFile or any file-like object
            raw_bytes = source.read()
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
        else:
            logger.error("Unsupported source type: %s", type(source))
            return ""

        return _extract_from_document(doc)

    except fitz.FileDataError as exc:
        # Corrupted or non-PDF file
        logger.warning("PDF appears to be corrupted or is not a valid PDF: %s", exc)
        return ""
    except Exception as exc:
        # Catch-all so the app never crashes from a bad upload
        logger.error("Unexpected error during PDF extraction: %s", exc)
        return ""


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------

def _extract_from_document(doc: "fitz.Document") -> str:
    """
    Iterate over all pages in an open PyMuPDF document and collect text.

    What we do per page:
    1. Extract text using PyMuPDF's "text" mode (preserves reading order).
    2. Clean the text (remove weird Unicode artefacts).
    3. Join pages with a double newline.

    Returns the combined text, or a warning string if no text was found
    (which usually indicates a scanned PDF).
    """
    if doc.page_count == 0:
        logger.warning("PDF has 0 pages — it may be empty or corrupted.")
        return ""

    page_texts = []

    for page_number in range(doc.page_count):
        page = doc.load_page(page_number)

        # "text" mode returns text in reading order (top-to-bottom,
        # left-to-right). It is the most useful mode for resumes.
        raw_text = page.get_text("text")

        # Light cleaning — preserve skill characters like C++ and .NET
        cleaned = clean_text(raw_text)

        if cleaned.strip():
            page_texts.append(cleaned)

    doc.close()

    if not page_texts:
        logger.warning(
            "No text extracted from PDF. "
            "This may be a scanned (image-only) PDF. "
            "OCR is not supported in Version 1."
        )
        return ""

    # Join pages with double newline to preserve section boundaries
    full_text = "\n\n".join(page_texts)
    logger.info("Extracted text from %d page(s), total chars: %d",
                len(page_texts), len(full_text))
    return full_text


def is_likely_scanned(text: str, min_chars: int = 100) -> bool:
    """
    Heuristic check: if we extracted very few characters from a PDF,
    it is probably a scanned document.

    Parameters
    ----------
    text       : The text returned by extract_text_from_pdf.
    min_chars  : Threshold below which we consider the PDF scanned.

    Returns
    -------
    bool — True means the PDF is probably scanned.
    """
    return len(text.strip()) < min_chars
