"""
Configuration module for DDR generation system.
Manages API keys, paths, severity rules, and correlation patterns.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from dotenv import load_dotenv

# CRITICAL: Load environment variables FIRST, before any os.getenv() calls
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)  # override=True ensures new values replace old ones


# ========== API Configuration ==========
@dataclass
class APIConfig:
    """API keys and endpoints configuration"""
    
    # LLM Provider: "openai", "gemini", "ollama", "groq"
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    
    # Model names
    openai_model: str = "gpt-4"
    gemini_model: str = "gemini-pro"  # Using v1 compatible model
    ollama_model: str = "llama3"
    groq_model: str = "llama-3.1-8b-instant"  # Using confirmed available model
    
    # Ollama endpoint (for local LLM)
    ollama_endpoint: str = "http://localhost:11434"


# ========== Path Configuration ==========
@dataclass
class PathConfig:
    """File paths and directories"""
    
    project_root: Path = Path(__file__).parent.parent
    data_dir: Path = field(init=False)
    samples_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    
    def __post_init__(self):
        self.data_dir = self.project_root / "ddr_generator" / "data"
        self.samples_dir = self.data_dir / "samples"
        self.output_dir = self.project_root / "ddr_generator" / "output"
        
        # Create directories if they don't exist
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# ========== Severity Rules Configuration ==========
@dataclass
class SeverityConfig:
    """Rules for severity assessment"""
    
    # Severity weights (0-1)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "leakage": 1.0,
        "dampness": 0.7,
        "crack": 0.6,
        "efflorescence": 0.5,
        "tile_gap": 0.4,
        "mild_dampness": 0.3,
    })
    
    # Area impact multipliers
    area_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "multiple_areas": 1.5,  # Issue in 3+ areas
        "structural": 1.8,       # External walls, ceiling
        "wet_areas": 1.3,        # Bathrooms, kitchen
    })
    
    # Severity thresholds
    high_threshold: float = 0.75
    medium_threshold: float = 0.45
    low_threshold: float = 0.0
    
    # Rules for severity calculation
    rules: Dict[str, Tuple[str, str]] = field(default_factory=lambda: {
        # (condition_pattern, severity_level)
        "active_leakage_plumbing": ("HIGH", "Active leakage with plumbing issues requires immediate attention"),
        "recurring_dampness": ("MEDIUM", "Recurring dampness across multiple areas indicates ongoing moisture ingress"),
        "external_crack_internal_damp": ("HIGH", "External cracks combined with internal dampness suggest water ingress"),
        "skirting_dampness_multiple": ("MEDIUM", "Skirting dampness in multiple rooms indicates ground-level moisture issue"),
        "tile_gaps_adjacent_damp": ("MEDIUM", "Tile joint gaps with adjacent area dampness suggest plumbing seepage"),
        "mild_isolated": ("LOW", "Mild and isolated dampness with no active leakage"),
    })


# ========== Correlation Rules Configuration ==========
@dataclass
class CorrelationConfig:
    """Rules for cross-area correlation"""
    
    # Correlation patterns: (negative_pattern, positive_pattern, root_cause)
    patterns: List[Tuple[str, str, str]] = field(default_factory=lambda: [
        (
            "skirting dampness",
            "tile joint gap",
            "Plumbing seepage from bathroom through tile joints causing dampness in adjacent room skirting"
        ),
        (
            "dampness",
            "external wall crack",
            "Water ingress through external wall cracks leading to internal dampness"
        ),
        (
            "ceiling leakage",
            "plumbing issue",
            "Plumbing leakage from above unit causing ceiling water damage"
        ),
        (
            "wall dampness",
            "tile joint gap",
            "Moisture migration through compromised tile joints in wet areas"
        ),
        (
            "efflorescence",
            "dampness",
            "Prolonged moisture exposure causing salt crystallization (efflorescence)"
        ),
    ])
    
    # Adjacent area mappings (for deduction)
    adjacent_areas: Dict[str, List[str]] = field(default_factory=lambda: {
        "common_bathroom": ["hall", "common_bedroom"],
        "master_bathroom": ["master_bedroom"],
        "kitchen": ["hall", "common_bedroom"],
        "parking": ["hall"],  # Below hall
    })
    
    # Keywords for area type classification
    area_keywords: Dict[str, List[str]] = field(default_factory=lambda: {
        "wet_area": ["bathroom", "kitchen", "toilet", "washroom"],
        "living_area": ["hall", "living", "drawing", "lounge"],
        "bedroom": ["bedroom", "master", "common"],
        "utility": ["parking", "balcony", "terrace", "corridor"],
    })


# ========== Extraction Patterns Configuration ==========
@dataclass
class ExtractionConfig:
    """Patterns for text extraction from PDFs"""
    
    # Keywords to identify negative findings
    negative_keywords: List[str] = field(default_factory=lambda: [
        "dampness", "leakage", "crack", "efflorescence", "seepage",
        "stain", "moisture", "wet", "damage", "deterioration"
    ])
    
    # Keywords to identify positive findings (causes/sources)
    positive_keywords: List[str] = field(default_factory=lambda: [
        "tile joint", "gap", "crack", "plumbing issue", "pipe",
        "external wall", "terrace", "drainage", "waterproofing"
    ])
    
    # Thermal temperature patterns
    thermal_patterns: Dict[str, float] = field(default_factory=lambda: {
        "cold_threshold": 23.0,  # Temperatures below this are cold spots
        "hot_threshold": 26.0,   # Temperatures above this are hot spots
        "significant_diff": 3.0,  # Temperature difference indicating issue
    })
    
    # Table detection keywords
    table_headers: List[str] = field(default_factory=lambda: [
        "impacted area", "exposed area", "negative side", "positive side",
        "area", "observation", "finding", "issue", "location"
    ])


# ========== Deduplication Configuration ==========
@dataclass
class DeduplicationConfig:
    """Settings for deduplication"""
    
    # Similarity threshold (0-1)
    similarity_threshold: float = 0.85
    
    # Use embedding-based similarity
    use_embeddings: bool = True
    
    # Sentence transformer model name
    embedding_model: str = "all-MiniLM-L6-v2"


# ========== Global Configuration Instance ==========
class Config:
    """Main configuration object"""
    
    def __init__(self):
        self.api = APIConfig()
        self.paths = PathConfig()
        self.severity = SeverityConfig()
        self.correlation = CorrelationConfig()
        self.extraction = ExtractionConfig()
        self.deduplication = DeduplicationConfig()
    
    def validate(self) -> bool:
        """Validate configuration"""
        if self.api.llm_provider == "openai" and not self.api.openai_api_key:
            raise ValueError("OpenAI API key not set. Please set OPENAI_API_KEY environment variable.")
        if self.api.llm_provider == "gemini" and not self.api.gemini_api_key:
            raise ValueError("Gemini API key not set. Please set GEMINI_API_KEY environment variable.")
        if self.api.llm_provider == "groq" and not self.api.groq_api_key:
            raise ValueError("Groq API key not set. Please set GROQ_API_KEY environment variable.")
        return True


# Create global config instance
config = Config()
