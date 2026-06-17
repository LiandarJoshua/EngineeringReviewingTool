from pathlib import Path
from typing import List, Dict, Any


def extract_requirements_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extract text and structured requirements from a PDF specification document.
    Returns a dict with raw text and a list of extracted requirement statements.
    """
    import pdfplumber

    full_text = []
    pages_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            full_text.append(text)
            pages_data.append({"page": i + 1, "text": text})

    combined = "\n\n".join(full_text)
    requirements = _extract_requirement_statements(combined)

    return {
        "source": pdf_path,
        "page_count": len(pages_data),
        "full_text": combined,
        "requirements": requirements,
        "word_count": len(combined.split()),
    }


def _extract_requirement_statements(text: str) -> List[str]:
    """
    Heuristic extraction of requirement statements.
    Looks for lines containing SHALL, MUST, SHOULD, MUST NOT, etc.
    """
    RFC_KEYWORDS = {"SHALL", "MUST", "SHOULD", "REQUIRED", "WILL", "MAY", "MUST NOT", "SHALL NOT"}
    requirements = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        upper = stripped.upper()
        if any(kw in upper for kw in RFC_KEYWORDS):
            requirements.append(stripped)
    return requirements
