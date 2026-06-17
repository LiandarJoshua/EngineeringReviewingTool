from typing import TypedDict, Optional, List, Dict, Any

ALL_STAGES = [
    "ingestion",
    "code_mapping",
    "architecture",
    "security",
    "scalability",
    "testing",
    "technical_debt",
    "requirements",
    "coaching",
    "prioritization",
    "synthesis",
]


class ReviewState(TypedDict):
    # Input
    review_id: str
    repo_id: str
    repo_url: str
    user_id: str
    requirements_pdf_path: Optional[str]

    # Computed during workflow
    local_path: str
    stack: Dict[str, Any]
    parsed_files: List[Dict]

    # Agent outputs
    architecture_findings: List[Dict]
    security_findings: List[Dict]
    scalability_findings: List[Dict]
    testing_findings: List[Dict]
    debt_findings: List[Dict]
    requirements_alignment: List[Dict]
    coaching_report: Dict
    prioritized_findings: List[Dict]
    final_report: Dict

    # Scores (0–100)
    scores: Dict[str, float]

    # Progress tracking
    stage_status: Dict[str, str]  # stage_name -> pending/running/complete/failed
    errors: List[str]
