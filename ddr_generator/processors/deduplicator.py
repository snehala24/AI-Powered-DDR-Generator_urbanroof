"""
Deduplication module: Removes duplicate observations using similarity matching.
Uses both rule-based and embedding-based approaches.
"""

from typing import List, Set
import re
from ..config import config


class Deduplicator:
    """Intelligent deduplication of observations"""
    
    def __init__(self):
        self.dedup_config = config.deduplication
        self.similarity_model = None
        
        # Initialize embedding model if configured
        if self.dedup_config.use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.similarity_model = SentenceTransformer(self.dedup_config.embedding_model)
            except ImportError:
                print("Warning: sentence-transformers not installed. Using rule-based deduplication only.")
                self.similarity_model = None
    
    def deduplicate_findings(self, findings: List[str]) -> List[str]:
        """
        Remove duplicate findings from a list
        
        Args:
            findings: List of observation strings
            
        Returns:
            Deduplicated list
        """
        if not findings:
            return []
        
        # Step 1: Remove exact duplicates (case-insensitive)
        unique_findings = self._remove_exact_duplicates(findings)
        
        # Step 2: Normalize and merge similar phrases
        unique_findings = self._merge_similar_normalized(unique_findings)
        
        # Step 3: Use embedding-based similarity if available
        if self.similarity_model and len(unique_findings) > 1:
            unique_findings = self._deduplicate_with_embeddings(unique_findings)
        
        return unique_findings
    
    def _remove_exact_duplicates(self, findings: List[str]) -> List[str]:
        """Remove exact duplicates (case-insensitive)"""
        seen = set()
        unique = []
        
        for finding in findings:
            normalized = finding.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(finding)
        
        return unique
    
    def _merge_similar_normalized(self, findings: List[str]) -> List[str]:
        """Merge findings that are similar after normalization"""
        if len(findings) <= 1:
            return findings
        
        # Normalize each finding
        normalized_map = {}
        for finding in findings:
            norm = self._normalize_text(finding)
            if norm not in normalized_map:
                normalized_map[norm] = finding
        
        return list(normalized_map.values())
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Remove common filler words
        fillers = ["observed", "noticed", "found", "seen", "mild", "slight", "minor"]
        for filler in fillers:
            text = re.sub(r'\b' + filler + r'\b', '', text)
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove extra spaces again
        text = " ".join(text.split())
        
        return text
    
    def _deduplicate_with_embeddings(self, findings: List[str]) -> List[str]:
        """Use semantic similarity to deduplicate"""
        if not self.similarity_model:
            return findings
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            # Generate embeddings
            embeddings = self.similarity_model.encode(findings)
            
            # Calculate pairwise similarities
            similarities = cosine_similarity(embeddings)
            
            # Find groups of similar findings
            threshold = self.dedup_config.similarity_threshold
            keep_indices = set(range(len(findings)))
            
            for i in range(len(findings)):
                if i not in keep_indices:
                    continue
                    
                for j in range(i + 1, len(findings)):
                    if j not in keep_indices:
                        continue
                    
                    # If very similar, keep only the longer/more detailed one
                    if similarities[i][j] >= threshold:
                        if len(findings[i]) >= len(findings[j]):
                            keep_indices.discard(j)
                        else:
                            keep_indices.discard(i)
                            break
            
            # Return findings that should be kept
            return [findings[i] for i in sorted(keep_indices)]
        
        except Exception as e:
            print(f"Warning: Embedding-based deduplication failed: {e}. Falling back to rule-based.")
            return findings
    
    def find_duplicates_across_areas(self, area_findings: dict) -> dict:
        """
        Find observations that appear in multiple areas
        
        Args:
            area_findings: Dict mapping area -> list of findings
            
        Returns:
            Dict mapping finding -> list of areas where it appears
        """
        finding_to_areas = {}
        
        for area, findings in area_findings.items():
            for finding in findings:
                norm = self._normalize_text(finding)
                if norm not in finding_to_areas:
                    finding_to_areas[norm] = {
                        "original_text": finding,
                        "areas": []
                    }
                finding_to_areas[norm]["areas"].append(area)
        
        # Filter to only cross-area duplicates
        cross_area = {
            data["original_text"]: data["areas"]
            for norm, data in finding_to_areas.items()
            if len(data["areas"]) > 1
        }
        
        return cross_area
