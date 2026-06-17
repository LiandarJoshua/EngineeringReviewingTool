from typing import List, Dict, Tuple


def compute_finding_metrics(
    predicted: List[Dict], expected: List[Dict]
) -> Tuple[float, float, float]:
    """
    Compute precision, recall, F1 for finding detection.
    A predicted finding matches if category AND file_path match an expected finding.
    """
    if not expected:
        return (1.0, 1.0, 1.0) if not predicted else (0.0, 1.0, 0.0)
    if not predicted:
        return (0.0, 0.0, 0.0)

    def matches(pred: Dict, exp: Dict) -> bool:
        cat_match = pred.get("category", "").lower() == exp.get("category", "").lower()
        file_match = (
            exp.get("file", "") in pred.get("file_path", "")
            or not exp.get("file")
        )
        return cat_match and file_match

    true_positives = 0
    matched_expected = set()
    for pred in predicted:
        for i, exp in enumerate(expected):
            if i not in matched_expected and matches(pred, exp):
                true_positives += 1
                matched_expected.add(i)
                break

    precision = true_positives / len(predicted)
    recall = true_positives / len(expected)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return round(precision, 3), round(recall, 3), round(f1, 3)


def compute_score_accuracy(predicted: Dict, expected_ranges: Dict) -> float:
    """
    Check if predicted scores fall within expected ranges.
    expected_ranges: {"security": (min, max), "testing": (min, max)}
    """
    if not expected_ranges:
        return 1.0
    in_range = sum(
        1 for k, (lo, hi) in expected_ranges.items()
        if lo <= predicted.get(k, -1) <= hi
    )
    return round(in_range / len(expected_ranges), 3)
