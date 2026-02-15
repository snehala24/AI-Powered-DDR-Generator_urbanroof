"""
Specialized parser for thermal imaging reports.
Extracts temperature readings, cold/hot spots, and area mappings.
"""

import re
from typing import Dict, List, Tuple, Any, Optional
from .pdf_parser import PDFParser
from ..schemas import ThermalEvidence
from ..config import config


class ThermalParser(PDFParser):
    """Parser for thermal imaging reports"""
    
    def __init__(self, pdf_path: str):
        """
        Initialize thermal report parser
        
        Args:
            pdf_path: Path to thermal PDF
        """
        super().__init__(pdf_path)
        self.thermal_config = config.extraction.thermal_patterns
    
    def parse(self) -> Dict[str, ThermalEvidence]:
        """
        Parse thermal report and extract temperature data
        
        Returns:
            Dictionary mapping area names to ThermalEvidence
        """
        thermal_data = {}
        
        # Extract all text
        all_text = self.extract_text_by_page()
        
        # Parse temperature readings from text
        for page_num, text in all_text.items():
            area_readings = self._extract_temperature_readings(text)
            thermal_data.update(area_readings)
        
        # Extract from tables if available
        tables = self.extract_tables()
        for table in tables:
            table_readings = self._parse_thermal_table(table)
            thermal_data.update(table_readings)
        
        return thermal_data
    
    def _extract_temperature_readings(self, text: str) -> Dict[str, ThermalEvidence]:
        """
        Extract temperature readings from text
        
        Args:
            text: Text content
            
        Returns:
            Dictionary of area to ThermalEvidence
        """
        readings = {}
        current_area = None
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to detect area name
            area_match = self._detect_area_in_line(line)
            if area_match:
                current_area = area_match
                if current_area not in readings:
                    readings[current_area] = ThermalEvidence()
            
            # Extract temperature readings
            temps = self._extract_temperatures(line)
            
            if temps and current_area:
                # Update thermal evidence for current area
                if current_area not in readings:
                    readings[current_area] = ThermalEvidence()
                
                evidence = readings[current_area]
                
                # Identify hot and cold spots
                for temp in temps:
                    if temp < self.thermal_config["cold_threshold"]:
                        if evidence.cold_spot_temp is None or temp < evidence.cold_spot_temp:
                            evidence.cold_spot_temp = temp
                            evidence.has_cold_zones = True
                    
                    if temp > self.thermal_config["hot_threshold"]:
                        if evidence.hot_spot_temp is None or temp > evidence.hot_spot_temp:
                            evidence.hot_spot_temp = temp
                
                # Calculate temperature difference
                if evidence.cold_spot_temp and evidence.hot_spot_temp:
                    evidence.temp_difference = round(evidence.hot_spot_temp - evidence.cold_spot_temp, 1)
            
            # Look for specific cold/hot spot markers
            if "cold" in line.lower() and current_area:
                temp = self._extract_single_temperature(line)
                if temp and current_area in readings:
                    if readings[current_area].cold_spot_temp is None or temp < readings[current_area].cold_spot_temp:
                        readings[current_area].cold_spot_temp = temp
                        readings[current_area].has_cold_zones = True
            
            if "hot" in line.lower() and current_area:
                temp = self._extract_single_temperature(line)
                if temp and current_area in readings:
                    if readings[current_area].hot_spot_temp is None or temp > readings[current_area].hot_spot_temp:
                        readings[current_area].hot_spot_temp = temp
        
        # Calculate average temperatures and differences
        for area, evidence in readings.items():
            if evidence.cold_spot_temp and evidence.hot_spot_temp:
                evidence.avg_temp = round((evidence.cold_spot_temp + evidence.hot_spot_temp) / 2, 1)
                evidence.temp_difference = round(evidence.hot_spot_temp - evidence.cold_spot_temp, 1)
        
        return readings
    
    def _parse_thermal_table(self, table: List[List[str]]) -> Dict[str, ThermalEvidence]:
        """
        Parse thermal data from table
        
        Args:
            table: Table data (list of rows)
            
        Returns:
            Dictionary of area to ThermalEvidence
        """
        readings = {}
        
        if not table or len(table) < 2:
            return readings
        
        # Identify columns
        header = [str(cell).lower() if cell else "" for cell in table[0]]
        area_col = self._find_column(header, ["area", "location", "room"])
        temp_col = self._find_column(header, ["temperature", "temp", "reading", "°c"])
        
        if area_col is None:
            return readings
        
        # Parse rows
        for row in table[1:]:
            if len(row) <= area_col:
                continue
            
            area = str(row[area_col]).strip() if row[area_col] else ""
            if not area or area.lower() in ["none", "n/a", "-"]:
                continue
            
            area = area.title()
            
            # Extract temperatures from the row
            row_text = " ".join([str(cell) for cell in row if cell])
            temps = self._extract_temperatures(row_text)
            
            if temps:
                if area not in readings:
                    readings[area] = ThermalEvidence()
                
                min_temp = min(temps)
                max_temp = max(temps)
                
                if min_temp < self.thermal_config["cold_threshold"]:
                    readings[area].cold_spot_temp = min_temp
                    readings[area].has_cold_zones = True
                
                if max_temp > self.thermal_config["hot_threshold"]:
                    readings[area].hot_spot_temp = max_temp
                
                readings[area].avg_temp = round(sum(temps) / len(temps), 1)
                readings[area].temp_difference = round(max_temp - min_temp, 1)
        
        return readings
    
    def _extract_temperatures(self, text: str) -> List[float]:
        """
        Extract all temperature values from text
        
        Args:
            text: Text content
            
        Returns:
            List of temperature values in Celsius
        """
        # Pattern to match temperature readings: 25.5°C, 25.5 C, 25.5°, 25.5
        pattern = r'(\d{1,2}\.?\d{0,2})\s*[°]?\s*[Cc]?'
        matches = re.findall(pattern, text)
        
        temps = []
        for match in matches:
            try:
                temp = float(match)
                # Reasonable temperature range for buildings (15-35°C)
                if 15 <= temp <= 40:
                    temps.append(temp)
            except ValueError:
                continue
        
        return temps
    
    def _extract_single_temperature(self, text: str) -> Optional[float]:
        """Extract a single temperature from text"""
        temps = self._extract_temperatures(text)
        return temps[0] if temps else None
    
    def _detect_area_in_line(self, line: str) -> Optional[str]:
        """
        Detect if line contains an area name
        
        Args:
            line: Text line
            
        Returns:
            Area name if detected, None otherwise
        """
        line_lower = line.lower()
        
        # Common area keywords
        area_keywords = [
            "hall", "bedroom", "bathroom", "kitchen", "parking",
            "balcony", "terrace", "living", "dining", "master", "common",
            "ceiling", "wall", "floor", "skirting"
        ]
        
        for keyword in area_keywords:
            if keyword in line_lower:
                # Extract the area phrase (usually 2-4 words)
                words = line.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        # Take surrounding words
                        start = max(0, i - 1)
                        end = min(len(words), i + 3)
                        area = " ".join(words[start:end])
                        
                        # Clean up
                        area = re.sub(r'[:\-–].*$', '', area)  # Remove anything after colon or dash
                        area = re.sub(r'[^\w\s]', '', area)     # Remove special chars
                        
                        return area.title().strip()
        
        return None
    
    def _find_column(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by keywords"""
        for i, cell in enumerate(header):
            if any(keyword in cell for keyword in keywords):
                return i
        return None
