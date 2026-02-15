"""
Core PDF extraction utilities using PyMuPDF and pdfplumber.
Handles text extraction, table detection, and image extraction.
"""

import io
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image


class PDFParser:
    """Base PDF parser with common extraction methods"""
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF parser
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.doc = fitz.open(pdf_path)
        self.num_pages = len(self.doc)
    
    def extract_text_by_page(self) -> Dict[int, str]:
        """
        Extract text from all pages
        
        Returns:
            Dictionary mapping page number to extracted text
        """
        texts = {}
        for page_num in range(self.num_pages):
            page = self.doc[page_num]
            texts[page_num] = page.get_text("text")
        return texts
    
    def extract_text_with_layout(self, page_num: int) -> str:
        """
        Extract text preserving layout structure
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Text with layout preservation
        """
        page = self.doc[page_num]
        return page.get_text("blocks")
    
    def extract_tables(self, page_num: Optional[int] = None) -> List[List[List[str]]]:
        """
        Extract tables from PDF using pdfplumber
        
        Args:
            page_num: Specific page number (None for all pages)
            
        Returns:
            List of tables, where each table is a list of rows
        """
        tables = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            pages_to_process = [pdf.pages[page_num]] if page_num is not None else pdf.pages
            
            for page in pages_to_process:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        
        return tables
    
    def find_tables_by_header(self, header_keywords: List[str]) -> List[Tuple[int, List[List[str]]]]:
        """
        Find tables containing specific header keywords
        
        Args:
            header_keywords: Keywords to search for in table headers
            
        Returns:
            List of (page_num, table) tuples
        """
        matching_tables = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue
                
                for table in tables:
                    if not table or not table[0]:  # Empty table
                        continue
                    
                    # Check if any header keyword is in first row
                    header_row = [str(cell).lower() if cell else "" for cell in table[0]]
                    header_text = " ".join(header_row)
                    
                    if any(keyword.lower() in header_text for keyword in header_keywords):
                        matching_tables.append((page_num, table))
        
        return matching_tables
    
    def extract_images(self, page_num: Optional[int] = None) -> List[Tuple[int, Image.Image]]:
        """
        Extract images from PDF
        
        Args:
            page_num: Specific page number (None for all pages)
            
        Returns:
            List of (page_num, PIL Image) tuples
        """
        images = []
        pages_to_process = [page_num] if page_num is not None else range(self.num_pages)
        
        for pnum in pages_to_process:
            page = self.doc[pnum]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image
                pil_image = Image.open(io.BytesIO(image_bytes))
                images.append((pnum, pil_image))
        
        return images
    
    def search_text(self, query: str, case_sensitive: bool = False) -> Dict[int, List[Tuple[str, Tuple]]]:
        """
        Search for text across all pages
        
        Args:
            query: Text to search for
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            Dictionary mapping page number to list of (matched_text, bounding_box) tuples
        """
        results = {}
        
        for page_num in range(self.num_pages):
            page = self.doc[page_num]
            search_results = page.search_for(query, quads=False)
            
            if search_results:
                results[page_num] = [(query, rect) for rect in search_results]
        
        return results
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extract PDF metadata
        
        Returns:
            Dictionary with metadata fields
        """
        metadata = self.doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "num_pages": self.num_pages,
        }
    
    def get_page_text_blocks(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Get structured text blocks from a page
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            List of text blocks with position and content
        """
        page = self.doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        structured_blocks = []
        for block in blocks:
            if block.get("type") == 0:  # Text block
                block_info = {
                    "bbox": block["bbox"],
                    "text": "",
                    "lines": []
                }
                
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    block_info["lines"].append(line_text)
                    block_info["text"] += line_text + " "
                
                block_info["text"] = block_info["text"].strip()
                structured_blocks.append(block_info)
        
        return structured_blocks
    
    def close(self):
        """Close the PDF document"""
        self.doc.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
