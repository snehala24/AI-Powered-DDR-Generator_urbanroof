"""
Data structurer: Converts raw extracted text into structured JSON format.
Merges inspection and thermal data into AreaObservation objects.
"""

from typing import Dict, List, Optional
from ..schemas import (
    ExtractionResult, AreaObservation, ThermalEvidence,
    PropertyDetails, DDRReport
)


class DataStructurer:
    """Converts raw extraction results to structured format"""
    
    def __init__(self):
        pass
    
    def structure_data(
        self,
        inspection_result: ExtractionResult,
        thermal_data: Dict[str, ThermalEvidence]
    ) -> DDRReport:
        """
        Convert raw extraction results to structured DDR report format
        
        Args:
            inspection_result: Raw inspection extraction results
            thermal_data: Dictionary of area -> ThermalEvidence
            
        Returns:
            DDRReport with structured area observations
        """
        # Collect all unique areas
        all_areas = set()
        all_areas.update(inspection_result.raw_negative_findings.keys())
        all_areas.update(inspection_result.raw_positive_findings.keys())
        all_areas.update(thermal_data.keys())
        
        # Create AreaObservation for each area
        areas = []
        for area_name in all_areas:
            area_obs = self._create_area_observation(
                area_name,
                inspection_result.raw_negative_findings.get(area_name, []),
                inspection_result.raw_positive_findings.get(area_name, []),
                thermal_data.get(area_name)
            )
            areas.append(area_obs)
        
        # Sort areas by severity (will be calculated later) and name
        areas.sort(key=lambda x: x.area_name)
        
        # Create DDR report
        report = DDRReport(
            property_details=inspection_result.property_details,
            areas=areas
        )
        
        return report
    
    def _create_area_observation(
        self,
        area_name: str,
        negative_findings: List[str],
        positive_findings: List[str],
        thermal_evidence: Optional[ThermalEvidence]
    ) -> AreaObservation:
        """
        Create AreaObservation from raw data
        
        Args:
            area_name: Name of the area
            negative_findings: List of issues found
            positive_findings: List of causes/sources
            thermal_evidence: Thermal data if available
            
        Returns:
            AreaObservation object
        """
        return AreaObservation(
            area_name=area_name,
            negative_findings=negative_findings,
            positive_findings=positive_findings,
            thermal_evidence=thermal_evidence
        )
    
    def merge_similar_areas(self, report: DDRReport) -> DDRReport:
        """
        Merge observations from similar areas (e.g., "Hall" and "hall skirting")
        
        Args:
            report: DDR report
            
        Returns:
            Report with merged areas
        """
        # Group areas by base name
        area_groups: Dict[str, List[AreaObservation]] = {}
        
        for area in report.areas:
            base_name = self._get_base_area_name(area.area_name)
            if base_name not in area_groups:
                area_groups[base_name] = []
            area_groups[base_name].append(area)
        
        # Merge areas within each group
        merged_areas = []
        for base_name, group in area_groups.items():
            if len(group) == 1:
                merged_areas.append(group[0])
            else:
                merged = self._merge_area_observations(base_name, group)
                merged_areas.append(merged)
        
        report.areas = merged_areas
        return report
    
    def _get_base_area_name(self, area_name: str) -> str:
        """Extract base area name (remove skirting, ceiling, wall, etc.)"""
        base = area_name.lower()
        
        # Remove specific location qualifiers
        qualifiers = ["skirting", "ceiling", "wall", "floor", "corner", "external", "internal"]
        for qualifier in qualifiers:
            base = base.replace(qualifier, "").strip()
        
        # Clean up
        base = " ".join(base.split())  # Remove extra spaces
        return base.title()
    
    def _merge_area_observations(
        self,
        base_name: str,
        observations: List[AreaObservation]
    ) -> AreaObservation:
        """Merge multiple area observations into one"""
        merged = AreaObservation(area_name=base_name)
        
        all_negative = []
        all_positive = []
        thermal_evidences = []
        
        for obs in observations:
            all_negative.extend(obs.negative_findings)
            all_positive.extend(obs.positive_findings)
            if obs.thermal_evidence:
                thermal_evidences.append(obs.thermal_evidence)
        
        # Remove duplicates while preserving order
        merged.negative_findings = list(dict.fromkeys(all_negative))
        merged.positive_findings = list(dict.fromkeys(all_positive))
        
        # Merge thermal evidence (take min cold, max hot)
        if thermal_evidences:
            merged_thermal = ThermalEvidence()
            
            cold_temps = [t.cold_spot_temp for t in thermal_evidences if t.cold_spot_temp]
            hot_temps = [t.hot_spot_temp for t in thermal_evidences if t.hot_spot_temp]
            
            if cold_temps:
                merged_thermal.cold_spot_temp = min(cold_temps)
                merged_thermal.has_cold_zones = True
            if hot_temps:
                merged_thermal.hot_spot_temp = max(hot_temps)
            
            if merged_thermal.cold_spot_temp and merged_thermal.hot_spot_temp:
                merged_thermal.temp_difference = round(
                    merged_thermal.hot_spot_temp - merged_thermal.cold_spot_temp, 1
                )
                merged_thermal.avg_temp = round(
                    (merged_thermal.hot_spot_temp + merged_thermal.cold_spot_temp) / 2, 1
                )
            
            merged.thermal_evidence = merged_thermal
        
        return merged
