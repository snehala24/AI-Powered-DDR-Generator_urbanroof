"""
Validation utilities for data quality checks.
"""

from typing import List, Dict, Any
from ..schemas import DDRReport, AreaObservation


def validate_report_completeness(report: DDRReport) -> Dict[str, Any]:
    """
    Validate report completeness and quality
    
    Returns:
        Dictionary with validation results
    """
    issues = []
    warnings = []
    
    # Check property details
    if not report.property_details.address:
        warnings.append("Missing property address")
    if not report.property_details.inspection_date:
        warnings.append("Missing inspection date")
    
    # Check areas
    if not report.areas:
        issues.append("No areas found in report")
    else:
        areas_with_issues = [a for a in report.areas if a.has_issues()]
        if not areas_with_issues:
            warnings.append("No issues found in any area")
    
    # Check for empty findings
    for area in report.areas:
        if area.negative_findings:
            for finding in area.negative_findings:
                if len(finding.strip()) < 3:
                    warnings.append(f"Very short finding in {area.area_name}: '{finding}'")
    
    # Check severity assessment
    if not report.severity_assessment:
        warnings.append("Missing severity assessment")
    
    # Check correlation
    if not report.correlation_result:
        warnings.append("Missing correlation analysis")
    
    # Check generated sections
    if not report.property_issue_summary:
        issues.append("Missing property issue summary")
    if not report.area_wise_observations:
        issues.append("Missing area-wise observations")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "score": calculate_quality_score(report)
    }


def calculate_quality_score(report: DDRReport) -> float:
    """
    Calculate report quality score (0-1)
    
    Returns:
        Quality score
    """
    score = 0.0
    max_score = 10.0
    
    # Property details (1 point)
    if report.property_details.address:
        score += 0.5
    if report.property_details.inspection_date:
        score += 0.5
    
    # Areas with data (2 points)
    if report.areas:
        score += 2.0
    
    # Thermal evidence (1 point)
    thermal_count = sum(1 for a in report.areas if a.thermal_evidence)
    if thermal_count > 0:
        score += min(1.0, thermal_count / len(report.areas) if report.areas else 0)
    
    # Correlation (2 points)
    if report.correlation_result:
        score += 1.0
        if report.correlation_result.root_causes:
            score += 1.0
    
    # Severity assessment (2 points)
    if report.severity_assessment:
        score += 2.0
    
    # Generated content (2 points)
    if report.property_issue_summary:
        score += 0.5
    if report.area_wise_observations:
        score += 0.5
    if report.probable_root_cause:
        score += 0.5
    if report.recommended_actions:
        score += 0.5
    
    return round(score / max_score, 2)


def check_for_hallucinations(
    generated_text: str,
    source_data: List[str]
) -> List[str]:
    """
    Basic check for potential hallucinations in generated text
    
    Args:
        generated_text: LLM-generated text
        source_data: Original source findings
        
    Returns:
        List of potential hallucinations
    """
    hallucinations = []
    
    # Check for specific numbers/measurements not in source
    import re
    numbers_in_generated = set(re.findall(r'\d+(?:\.\d+)?', generated_text))
    numbers_in_source = set()
    for source in source_data:
        numbers_in_source.update(re.findall(r'\d+(?:\.\d+)?', source))
    
    unexpected_numbers = numbers_in_generated - numbers_in_source
    if unexpected_numbers:
        hallucinations.append(
            f"Numbers not in source data: {', '.join(unexpected_numbers)}"
        )
    
    # Check for specific technical terms not in source
    technical_terms = [
        "asbestos", "mold", "mildew", "fungus", "structural failure",
        "foundation", "subsidence", "settlement"
    ]
    
    for term in technical_terms:
        if term.lower() in generated_text.lower():
            source_has_term = any(term.lower() in s.lower() for s in source_data)
            if not source_has_term:
                hallucinations.append(f"Technical term not in source: '{term}'")
    
    return hallucinations
