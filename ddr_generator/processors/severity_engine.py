"""
Severity assessment engine: Calculates severity scores and provides reasoning.
Uses multi-factor weighted scoring based on configuration rules.
"""

from typing import List, Tuple, Optional
from ..schemas import DDRReport, SeverityAssessment, AreaObservation
from ..config import config


class SeverityEngine:
    """Assesses severity of issues with reasoning"""
    
    def __init__(self):
        self.severity_config = config.severity
        self.weights = self.severity_config.weights
        self.multipliers = self.severity_config.area_multipliers
        self.rules = self.severity_config.rules
    
    def assess_severity(self, report: DDRReport) -> SeverityAssessment:
        """
        Assess overall severity and assign priorities
        
        Args:
            report: DDR report with areas and correlations
            
        Returns:
            SeverityAssessment with scores and reasoning
        """
        # Calculate severity for each area
        for area in report.areas:
            score, reasoning = self._calculate_area_severity(area, report.areas)
            area.severity_score = score
            area.severity = self._score_to_level(score)
        
        # Calculate overall severity
        area_scores = [area.severity_score for area in report.areas if area.severity_score]
        
        if not area_scores:
            overall_score = 0.0
            overall_level = "LOW"
            reasoning = "No significant issues identified"
        else:
            # Overall is weighted average, with emphasis on maximum
            overall_score = (max(area_scores) * 0.6 + sum(area_scores) / len(area_scores) * 0.4)
            overall_score = min(1.0, overall_score)  # Cap at 1.0
            overall_level = self._score_to_level(overall_score)
            reasoning = self._generate_overall_reasoning(report, overall_score)
        
        # Categorize areas by priority
        high_priority = [a.area_name for a in report.areas if a.severity == "HIGH"]
        medium_priority = [a.area_name for a in report.areas if a.severity == "MEDIUM"]
        low_priority = [a.area_name for a in report.areas if a.severity == "LOW"]
        
        return SeverityAssessment(
            overall_severity=overall_level,
            severity_score=round(overall_score, 2),
            reasoning=reasoning,
            high_priority_areas=high_priority,
            medium_priority_areas=medium_priority,
            low_priority_areas=low_priority
        )
    
    def _calculate_area_severity(
        self,
        area: AreaObservation,
        all_areas: List[AreaObservation]
    ) -> Tuple[float, str]:
        """
        Calculate severity score for a specific area
        
        Returns:
            Tuple of (score, reasoning)
        """
        if not area.has_issues():
            return 0.0, "No issues found"
        
        score = 0.0
        reasoning_parts = []
        
        # Factor 1: Type and severity of findings
        for finding in area.negative_findings:
            finding_lower = finding.lower()
            
            for keyword, weight in self.weights.items():
                if keyword in finding_lower:
                    score += weight
                    reasoning_parts.append(f"{keyword} detected")
        
        # Factor 2: Number of issues
        issue_count = len(area.negative_findings) + len(area.positive_findings)
        if issue_count >= 3:
            score *= 1.2
            reasoning_parts.append(f"multiple issues ({issue_count} findings)")
        
        # Factor 3: Thermal evidence
        if area.thermal_evidence and area.thermal_evidence.has_cold_zones:
            score *= 1.15
            reasoning_parts.append("thermal evidence of moisture")
        
        # Factor 4: Area type multiplier
        area_lower = area.area_name.lower()
        for area_type, multiplier in self.multipliers.items():
            if area_type == "structural" and any(k in area_lower for k in ["wall", "ceiling", "external"]):
                score *= multiplier
                reasoning_parts.append("structural element affected")
            elif area_type == "wet_areas" and any(k in area_lower for k in ["bathroom", "kitchen"]):
                score *= multiplier
                reasoning_parts.append("wet area concerns")
        
        # Check if issue appears in multiple areas
        area_issue_keywords = self._extract_keywords(area.negative_findings)
        similar_count = sum(
            1 for other in all_areas
            if other.area_name != area.area_name and
            any(kw in self._extract_keywords(other.negative_findings) for kw in area_issue_keywords)
        )
        
        if similar_count >= 2:
            score *= self.multipliers["multiple_areas"]
            reasoning_parts.append(f"similar issues in {similar_count + 1} areas")
        
        # Apply rule-based adjustments
        rule_match = self._match_severity_rules(area, all_areas)
        if rule_match:
            rule_level, rule_reason = rule_match
            reasoning_parts.append(rule_reason)
            
            # Boost score if high-severity rule matched
            if rule_level == "HIGH":
                score = max(score, 0.8)
        
        # Normalize score to 0-1 range
        score = min(1.0, score)
        
        # Generate reasoning
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "General assessment"
        
        return round(score, 2), reasoning
    
    def _match_severity_rules(
        self,
        area: AreaObservation,
        all_areas: List[AreaObservation]
    ) -> Optional[Tuple[str, str]]:
        """Check if area matches any predefined severity rules"""
        all_text = " ".join(area.negative_findings + area.positive_findings).lower()
        
        # Check active leakage + plumbing
        if "leakage" in all_text and "plumbing" in all_text:
            return self.rules["active_leakage_plumbing"]
        
        # Check external crack + internal dampness
        if "crack" in all_text and "dampness" in all_text:
            return self.rules["external_crack_internal_damp"]
        
        # Check recurring dampness (in findings)
        dampness_areas = [a for a in all_areas if any("dampness" in f.lower() for f in a.negative_findings)]
        if len(dampness_areas) >= 3:
            return self.rules["recurring_dampness"]
        
        # Check skirting dampness in multiple areas
        if "skirting" in area.area_name.lower() and "dampness" in all_text:
            skirting_count = sum(1 for a in all_areas if "skirting" in a.area_name.lower())
            if skirting_count >= 2:
                return self.rules["skirting_dampness_multiple"]
        
        # Check tile gaps + dampness
        if ("tile" in all_text and "gap" in all_text) and "dampness" in all_text:
            return self.rules["tile_gaps_adjacent_damp"]
        
        # Check mild isolated issues
        if "mild" in all_text and len(area.negative_findings) == 1:
            return self.rules["mild_isolated"]
        
        return None
    
    def _score_to_level(self, score: float) -> str:
        """Convert numerical score to severity level"""
        if score >= self.severity_config.high_threshold:
            return "HIGH"
        elif score >= self.severity_config.medium_threshold:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _extract_keywords(self, findings: List[str]) -> List[str]:
        """Extract key issue keywords from findings"""
        keywords = []
        for finding in findings:
            finding_lower = finding.lower()
            for keyword in self.weights.keys():
                if keyword in finding_lower:
                    keywords.append(keyword)
        return list(set(keywords))
    
    def _generate_overall_reasoning(self, report: DDRReport, overall_score: float) -> str:
        """Generate overall severity reasoning"""
        parts = []
        
        # Count areas by severity
        high_count = sum(1 for a in report.areas if a.severity == "HIGH")
        medium_count = sum(1 for a in report.areas if a.severity == "MEDIUM")
        low_count = sum(1 for a in report.areas if a.severity == "LOW")
        
        if high_count > 0:
            parts.append(f"{high_count} area(s) require immediate attention")
        if medium_count > 0:
            parts.append(f"{medium_count} area(s) need monitoring and remediation")
        if low_count > 0:
            parts.append(f"{low_count} area(s) have minor issues")
        
        # Add root cause summary if available
        if report.correlation_result and report.correlation_result.root_causes:
            cause_count = len(report.correlation_result.root_causes)
            parts.append(f"{cause_count} probable root cause(s) identified")
        
        # Overall assessment
        level = self._score_to_level(overall_score)
        if level == "HIGH":
            parts.append("Immediate professional intervention recommended")
        elif level == "MEDIUM":
            parts.append("Timely remediation advised to prevent escalation")
        else:
            parts.append("Regular monitoring recommended")
        
        return ". ".join(parts) + "."
