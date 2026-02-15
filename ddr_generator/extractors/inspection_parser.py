"""
Specialized parser for inspection reports.
Extracts area-wise findings, negative observations, and positive observations.
"""

import re
from typing import Dict, List, Tuple, Optional
from .pdf_parser import PDFParser
from ..schemas import PropertyDetails, ExtractionResult
from ..config import config


class InspectionParser(PDFParser):
    """Parser for inspection reports"""
    
    def __init__(self, pdf_path: str):
        """
        Initialize inspection report parser
        
        Args:
            pdf_path: Path to inspection PDF
        """
        super().__init__(pdf_path)
        self.extraction_config = config.extraction
    
    def parse(self) -> ExtractionResult:
        """
        Parse inspection report  and extract structured data
        
        Returns:
            ExtractionResult with property details and findings
        """
        # Extract metadata
        property_details = self._extract_property_details()
        
        # Find and parse summary table
        negative_findings, positive_findings = self._parse_summary_table()
        
        # If no table found, try text-based extraction
        if not negative_findings and not positive_findings:
            negative_findings, positive_findings = self._parse_by_text()
        
        # Extract additional metadata
        extraction_metadata = {
            "num_pages": self.num_pages,
            "extraction_method": "table" if negative_findings or positive_findings else "text",
            "areas_found": len(set(list(negative_findings.keys()) + list(positive_findings.keys())))
        }
        
        return ExtractionResult(
            property_details=property_details,
            raw_negative_findings=negative_findings,
            raw_positive_findings=positive_findings,
            thermal_data={},
            extraction_metadata=extraction_metadata
        )
    
    def _extract_property_details(self) -> PropertyDetails:
        """Extract property metadata from first page"""
        # Extract text from first page
        first_page_text = self.extract_text_by_page()[0]
        
        # Try to extract property ID, address, date, etc.
        property_details = PropertyDetails()
        
        # Search for common patterns
        address_match = re.search(r'(?:address|location|property)[:\s]+([^\n]+)', first_page_text, re.IGNORECASE)
        if address_match:
            property_details.address = address_match.group(1).strip()
        
        date_match = re.search(r'(?:date|inspection date)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', first_page_text, re.IGNORECASE)
        if date_match:
            property_details.inspection_date = date_match.group(1).strip()
        
        inspector_match = re.search(r'(?:inspector|inspected by)[:\s]+([^\n]+)', first_page_text, re.IGNORECASE)
        if inspector_match:
            property_details.inspector_name = inspector_match.group(1).strip()
        
        return property_details
    
    def _parse_summary_table(self) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Parse summary table from inspection report
        
        Returns:
            Tuple of (negative_findings, positive_findings) dictionaries
        """
        negative_findings = {}
        positive_findings = {}
        
        # Find tables with relevant headers
        table_headers = self.extraction_config.table_headers
        tables = self.find_tables_by_header(table_headers)
        
        for page_num, table in tables:
            # Identify column indices
            header_row = [str(cell).lower() if cell else "" for cell in table[0]]
            
            # Find area and observation columns
            area_col = self._find_column_index(header_row, ["area", "location", "impacted area", "exposed area"])
            obs_col = self._find_column_index(header_row, ["observation", "finding", "issue", "description"])
            
            if area_col is None or obs_col is None:
                continue
            
            # Determine if this is negative or positive side
            is_negative = any(keyword in " ".join(header_row) for keyword in ["impacted", "negative", "issue"])
            is_positive = any(keyword in " ".join(header_row) for keyword in ["exposed", "positive", "cause"])
            
            # Parse rows (skip header)
            for row in table[1:]:
                if len(row) <= max(area_col, obs_col):
                    continue
                
                area = str(row[area_col]).strip() if row[area_col] else ""
                observation = str(row[obs_col]).strip() if row[obs_col] else ""
                
                if not area or not observation or area.lower() in ["none", "n/a", "-"]:
                    continue
                
                # Clean area name
                area = self._clean_area_name(area)
                
                # Categorize based on table type
                if is_negative:
                    if area not in negative_findings:
                        negative_findings[area] = []
                    negative_findings[area].append(observation)
                elif is_positive:
                    if area not in positive_findings:
                        positive_findings[area] = []
                    positive_findings[area].append(observation)
                else:
                    # Default: categorize by observation keywords
                    if self._is_negative_finding(observation):
                        if area not in negative_findings:
                            negative_findings[area] = []
                        negative_findings[area].append(observation)
                    else:
                        if area not in positive_findings:
                            positive_findings[area] = []
                        positive_findings[area].append(observation)
        
        return negative_findings, positive_findings
    
    def _parse_by_text(self) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Fallback parser using text-based extraction when tables not found
        
        Returns:
            Tuple of (negative_findings, positive_findings) dictionaries
        """
        negative_findings = {}
        positive_findings = {}
        
        # Extract all text
        all_text = self.extract_text_by_page()
        
        current_section = None
        current_area = None
        
        for page_num, text in all_text.items():
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect section headers
                if re.search(r'(impacted|negative|issue)', line, re.IGNORECASE):
                    current_section = "negative"
                    continue
                elif re.search(r'(exposed|positive|cause)', line, re.IGNORECASE):
                    current_section = "positive"
                    continue
                
                # Try to detect area names (usually capitalized or contain room types)
                if self._is_area_name(line):
                    current_area = self._clean_area_name(line)
                    continue
                
                # Extract observations
                if current_area and current_section:
                    if self._is_observation(line):
                        if current_section == "negative":
                            if current_area not in negative_findings:
                                negative_findings[current_area] = []
                            negative_findings[current_area].append(line)
                        elif current_section == "positive":
                            if current_area not in positive_findings:
                                positive_findings[current_area] = []
                            positive_findings[current_area].append(line)
        
        return negative_findings, positive_findings
    
    def _find_column_index(self, header_row: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by matching keywords"""
        for i, cell in enumerate(header_row):
            if any(keyword in cell for keyword in keywords):
                return i
        return None
    
    def _clean_area_name(self, area: str) -> str:
        """Standardize area names"""
        area = area.strip()
        
        # Remove common prefixes
        area = re.sub(r'^(area|location|room)[:\s]+', '', area, flags=re.IGNORECASE)
        
        # Capitalize properly
        return area.title()
    
    def _is_negative_finding(self, text: str) -> bool:
        """Check if observation is a negative finding"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.extraction_config.negative_keywords)
    
    def _is_area_name(self, text: str) -> bool:
        """Check if text is likely an area name"""
        text_lower = text.lower()
        area_keywords = ["hall", "bedroom", "bathroom", "kitchen", "parking", "balcony", "terrace", "living", "dining"]
        return any(keyword in text_lower for keyword in area_keywords) and len(text.split()) <= 4
    
    def _is_observation(self, text: str) -> bool:
        """Check if text is likely an observation"""
        # Observations usually have specific keywords and are longer
        if len(text.split()) < 2:
            return False
        
        keywords = self.extraction_config.negative_keywords + self.extraction_config.positive_keywords
        return any(keyword in text.lower() for keyword in keywords)
