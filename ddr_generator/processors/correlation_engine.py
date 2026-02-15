"""
Correlation engine: Links observations across areas and identifies root causes.
Implements rule-based correlation patterns.
"""

from typing import List, Dict, Tuple
import re
from ..schemas import DDRReport, RootCause, CorrelationResult, AreaObservation
from ..config import config


class CorrelationEngine:
    """Correlates findings across areas to identify root causes"""
    
    def __init__(self):
        self.correlation_config = config.correlation
        self.correlation_patterns = self.correlation_config.patterns
        self.adjacent_areas = self.correlation_config.adjacent_areas
    
    def correlate(self, report: DDRReport) -> CorrelationResult:
        """
        Perform correlation analysis on report
        
        Args:
            report: DDR report with area observations
            
        Returns:
            CorrelationResult with identified root causes and links
        """
        root_causes = []
        cross_area_links = {}
        conflicts = []
        
        # Apply correlation patterns
        for pattern in self.correlation_patterns:
            negative_pattern, positive_pattern, root_cause_desc = pattern
            
            matches = self._find_pattern_matches(
                report.areas,
                negative_pattern,
                positive_pattern
            )
            
            if matches:
                root_cause = self._create_root_cause(
                    root_cause_desc,
                    matches,
                    "High" if len(matches) >= 3 else "Medium"
                )
                root_causes.append(root_cause)
                
                # Add cross-area links
                for match in matches:
                    area, neg, pos = match
                    if area not in cross_area_links:
                        cross_area_links[area] = []
                    # Store as string, not dict (to match schema)
                    cross_area_links[area].append(
                        f"{root_cause_desc}: {neg} + {pos}"
                    )
        
        # Check for adjacent area correlations
        adjacent_correlations = self._find_adjacent_area_correlations(report.areas)
        for correlation in adjacent_correlations:
            root_causes.append(correlation)
        
        # Detect conflicts (contradictory findings)
        conflicts = self._detect_conflicts(report.areas)
        
        # Deduplicate root causes
        root_causes = self._deduplicate_root_causes(root_causes)
        
        return CorrelationResult(
            root_causes=root_causes,
            cross_area_links=cross_area_links,
            conflicts=conflicts
        )
    
    def _find_pattern_matches(
        self,
        areas: List[AreaObservation],
        negative_pattern: str,
        positive_pattern: str
    ) -> List[Tuple[str, str, str]]:
        """
        Find areas matching both negative and positive patterns
        
        Returns:
            List of (area_name, negative_finding, positive_finding) tuples
        """
        matches = []
        
        for area in areas:
            matching_negatives = [
                nf for nf in area.negative_findings
                if self._pattern_matches(nf, negative_pattern)
            ]
            
            matching_positives = [
                pf for pf in area.positive_findings
                if self._pattern_matches(pf, positive_pattern)
            ]
            
            # If we have both types of matches, it's a correlation
            if matching_negatives and matching_positives:
                for neg in matching_negatives:
                    for pos in matching_positives:
                        matches.append((area.area_name, neg, pos))
            
            # Also check if positive finding is in an adjacent area
            for other_area in areas:
                if other_area.area_name == area.area_name:
                    continue
                
                if self._are_areas_adjacent(area.area_name, other_area.area_name):
                    other_positives = [
                        pf for pf in other_area.positive_findings
                        if self._pattern_matches(pf, positive_pattern)
                    ]
                    
                    if matching_negatives and other_positives:
                        for neg in matching_negatives:
                            for pos in other_positives:
                                matches.append((
                                    f"{area.area_name} (adjacent to {other_area.area_name})",
                                    neg,
                                    pos
                                ))
        
        return matches
    
    def _pattern_matches(self, text: str, pattern: str) -> bool:
        """Check if text matches pattern (fuzzy keyword matching)"""
        text_lower = text.lower()
        pattern_lower = pattern.lower()
        
        # Split pattern into keywords
        keywords = pattern_lower.split()
        
        # Check if all keywords are present
        return all(keyword in text_lower for keyword in keywords)
    
    def _are_areas_adjacent(self, area1: str, area2: str) -> bool:
        """Check if two areas are adjacent based on configuration"""
        area1_lower = area1.lower()
        area2_lower = area2.lower()
        
        for key_area, adjacent_list in self.adjacent_areas.items():
            if key_area in area1_lower:
                if any(adj in area2_lower for adj in adjacent_list):
                    return True
            if key_area in area2_lower:
                if any(adj in area1_lower for adj in adjacent_list):
                    return True
        
        # Also consider areas with shared keywords as potentially adjacent
        shared_keywords = ["bedroom", "bathroom", "hall", "kitchen"]
        for keyword in shared_keywords:
            if keyword in area1_lower and keyword in area2_lower:
                return True
        
        return False
    
    def _find_adjacent_area_correlations(
        self,
        areas: List[AreaObservation]
    ) -> List[RootCause]:
        """Find correlations between adjacent areas"""
        correlations = []
        
        for i, area in enumerate(areas):
            for j, other_area in enumerate(areas[i + 1:], start=i + 1):
                if not self._are_areas_adjacent(area.area_name, other_area.area_name):
                    continue
                
                # Check if one has positive findings and the other has negative
                if area.positive_findings and other_area.negative_findings:
                    cause_desc = (
                        f"Issues in {other_area.area_name} likely caused by "
                        f"problems identified in adjacent {area.area_name}"
                    )
                    
                    root_cause = RootCause(
                        cause_description=cause_desc,
                        affected_areas=[area.area_name, other_area.area_name],
                        supporting_evidence=area.positive_findings + other_area.negative_findings,
                        confidence="Medium"
                    )
                    correlations.append(root_cause)
                
                elif other_area.positive_findings and area.negative_findings:
                    cause_desc = (
                        f"Issues in {area.area_name} likely caused by "
                        f"problems identified in adjacent {other_area.area_name}"
                    )
                    
                    root_cause = RootCause(
                        cause_description=cause_desc,
                        affected_areas=[area.area_name, other_area.area_name],
                        supporting_evidence=other_area.positive_findings + area.negative_findings,
                        confidence="Medium"
                    )
                    correlations.append(root_cause)
        
        return correlations
    
    def _create_root_cause(
        self,
        description: str,
        matches: List[Tuple[str, str, str]],
        confidence: str
    ) -> RootCause:
        """Create RootCause object from matches"""
        affected_areas = list(set([match[0] for match in matches]))
        supporting_evidence = []
        
        for area, neg, pos in matches:
            supporting_evidence.append(f"{area}: {neg}")
            supporting_evidence.append(f"{area}: {pos}")
        
        return RootCause(
            cause_description=description,
            affected_areas=affected_areas,
            supporting_evidence=list(set(supporting_evidence)),  # Deduplicate
            confidence=confidence
        )
    
    def _detect_conflicts(self, areas: List[AreaObservation]) -> List[str]:
        """Detect conflicting information in observations"""
        conflicts = []
        
        # Check for contradictory statements
        for area in areas:
            all_findings = area.negative_findings + area.positive_findings
            
            # Look for contradictions (e.g., "no issue" vs "severe dampness")
            positive_indicators = ["no issue", "no damage", "good condition", "satisfactory"]
            negative_indicators = ["severe", "critical", "major", "significant"]
            
            has_positive = any(
                any(indicator in finding.lower() for indicator in positive_indicators)
                for finding in all_findings
            )
            
            has_negative = any(
                any(indicator in finding.lower() for indicator in negative_indicators)
                for finding in all_findings
            )
            
            if has_positive and has_negative:
                conflicts.append(
                    f"Conflicting severity indicators in {area.area_name}: "
                    f"Both positive and negative condition statements found"
                )
        
        return conflicts
    
    def _deduplicate_root_causes(self, root_causes: List[RootCause]) -> List[RootCause]:
        """Remove duplicate or very similar root causes"""
        if len(root_causes) <= 1:
            return root_causes
        
        unique_causes = []
        seen_descriptions = set()
        
        for cause in root_causes:
            # Normalize description
            norm_desc = cause.cause_description.lower().strip()
            
            if norm_desc not in seen_descriptions:
                seen_descriptions.add(norm_desc)
                unique_causes.append(cause)
            else:
                # Merge with existing cause
                for existing in unique_causes:
                    if existing.cause_description.lower().strip() == norm_desc:
                        # Merge affected areas and evidence
                        existing.affected_areas = list(set(
                            existing.affected_areas + cause.affected_areas
                        ))
                        existing.supporting_evidence = list(set(
                            existing.supporting_evidence + cause.supporting_evidence
                        ))
                        break
        
        return unique_causes
