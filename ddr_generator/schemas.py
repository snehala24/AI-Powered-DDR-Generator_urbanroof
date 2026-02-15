"""
Data models and schemas for DDR generation system.
Uses Pydantic for validation and type safety.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ========== Property Details Schema ==========
class PropertyDetails(BaseModel):
    """Property information metadata"""
    property_id: Optional[str] = Field(None, description="Property identifier")
    address: Optional[str] = Field(None, description="Property address")
    inspection_date: Optional[str] = Field(None, description="Date of inspection")
    inspector_name: Optional[str] = Field(None, description="Name of inspector")
    report_type: str = Field("Structural Diagnostic Report", description="Type of report")
    

# ========== Thermal Evidence Schema ==========
class ThermalEvidence(BaseModel):
    """Thermal imaging data for an area"""
    cold_spot_temp: Optional[float] = Field(None, description="Coldest temperature detected (°C)")
    hot_spot_temp: Optional[float] = Field(None, description="Hottest temperature detected (°C)")
    avg_temp: Optional[float] = Field(None, description="Average temperature (°C)")
    temp_difference: Optional[float] = Field(None, description="Temperature differential (°C)")
    has_cold_zones: bool = Field(False, description="Whether cold zones detected")
    thermal_notes: Optional[str] = Field(None, description="Additional thermal observations")
    
    def summary(self) -> str:
        """Generate human-readable thermal summary"""
        if not self.cold_spot_temp and not self.hot_spot_temp:
            return "Not Available"
        
        parts = []
        if self.cold_spot_temp:
            parts.append(f"Cold spot: {self.cold_spot_temp}°C")
        if self.hot_spot_temp:
            parts.append(f"Hot spot: {self.hot_spot_temp}°C")
        if self.temp_difference:
            parts.append(f"Δ{self.temp_difference}°C")
        
        result = ", ".join(parts)
        if self.has_cold_zones:
            result += " (Cold zones indicate moisture presence)"
        
        return result


# ========== Area Observation Schema ==========
class AreaObservation(BaseModel):
    """Observations for a specific area"""
    area_name: str = Field(..., description="Name of the area (e.g., 'Hall', 'Master Bedroom')")
    negative_findings: List[str] = Field(default_factory=list, description="Issues found (negative side)")
    positive_findings: List[str] = Field(default_factory=list, description="Exposed causes (positive side)")
    thermal_evidence: Optional[ThermalEvidence] = Field(None, description="Thermal imaging data")
    severity: Optional[str] = Field(None, description="Severity level: HIGH, MEDIUM, LOW")
    severity_score: Optional[float] = Field(None, description="Numerical severity (0-1)")
    
    def has_issues(self) -> bool:
        """Check if area has any issues"""
        return len(self.negative_findings) > 0 or len(self.positive_findings) > 0


# ========== Root Cause Schema ==========
class RootCause(BaseModel):
    """Identified root cause with supporting evidence"""
    cause_description: str = Field(..., description="Description of root cause")
    affected_areas: List[str] = Field(default_factory=list, description="Areas affected by this cause")
    supporting_evidence: List[str] = Field(default_factory=list, description="Evidence supporting this cause")
    confidence: str = Field("Medium", description="Confidence level: High, Medium, Low")


# ========== Correlation Result Schema ==========
class CorrelationResult(BaseModel):
    """Result from correlation analysis"""
    root_causes: List[RootCause] = Field(default_factory=list, description="Identified root causes")
    cross_area_links: Dict[str, List[str]] = Field(default_factory=dict, description="Area-to-area relationships")
    conflicts: List[str] = Field(default_factory=list, description="Data conflicts detected")
    

# ========== Severity Assessment Schema ==========
class SeverityAssessment(BaseModel):
    """Severity assessment with reasoning"""
    overall_severity: str = Field(..., description="Overall severity: HIGH, MEDIUM, LOW")
    severity_score: float = Field(..., ge=0.0, le=1.0, description="Numerical severity 0-1")
    reasoning: str = Field(..., description="Explanation for severity rating")
    high_priority_areas: List[str] = Field(default_factory=list, description="Areas requiring immediate attention")
    medium_priority_areas: List[str] = Field(default_factory=list, description="Areas needing monitoring")
    low_priority_areas: List[str] = Field(default_factory=list, description="Areas with minor issues")


# ========== DDR Report Schema ==========
class DDRReport(BaseModel):
    """Complete Detailed Diagnostic Report"""
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation timestamp")
    property_details: PropertyDetails = Field(..., description="Property information")
    
    # Observations
    areas: List[AreaObservation] = Field(default_factory=list, description="Area-wise observations")
    
    # Analysis
    correlation_result: Optional[CorrelationResult] = Field(None, description="Correlation analysis")
    severity_assessment: Optional[SeverityAssessment] = Field(None, description="Severity assessment")
    
    # Report sections (generated by LLM)
    property_issue_summary: str = Field("", description="Executive summary of issues")
    area_wise_observations: str = Field("", description="Detailed area observations")
    probable_root_cause: str = Field("", description="Root cause analysis")
    recommended_actions: str = Field("", description="Recommended remedial actions")
    additional_notes: str = Field("", description="Additional observations")
    missing_information: List[str] = Field(default_factory=list, description="Information not available")
    
    def get_all_affected_areas(self) -> List[str]:
        """Get list of all areas with issues"""
        return [area.area_name for area in self.areas if area.has_issues()]
    
    def count_total_issues(self) -> int:
        """Count total number of findings"""
        total = 0
        for area in self.areas:
            total += len(area.negative_findings) + len(area.positive_findings)
        return total


# ========== Extraction Result Schema ==========
class ExtractionResult(BaseModel):
    """Raw extraction results from PDF parsing"""
    property_details: PropertyDetails = Field(..., description="Property metadata")
    raw_negative_findings: Dict[str, List[str]] = Field(default_factory=dict, description="Area -> negative findings")
    raw_positive_findings: Dict[str, List[str]] = Field(default_factory=dict, description="Area -> positive findings")
    thermal_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Area -> thermal readings")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extraction stats")


# ========== Document Input Schema ==========
class DocumentInput(BaseModel):
    """Input documents for processing"""
    inspection_pdf_path: str = Field(..., description="Path to inspection report PDF")
    thermal_pdf_path: Optional[str] = Field(None, description="Path to thermal report PDF")
    output_format: str = Field("markdown", description="Output format: markdown, json, both")
    output_path: Optional[str] = Field(None, description="Custom output path")
