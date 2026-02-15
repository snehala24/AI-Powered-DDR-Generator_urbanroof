"""
Main pipeline orchestrator for DDR generation.
Coordinates all modules to generate complete reports from PDFs.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path to allow direct execution
if __name__ == "__main__":
    # Get the parent directory (project root)
    current_dir = Path(__file__).parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

# Try relative imports first (when run as module), fall back to absolute
try:
    # Extractors
    from .extractors import InspectionParser, ThermalParser
    
    # Processors
    from .processors import (
        DataStructurer,
        Deduplicator,
        CorrelationEngine,
        SeverityEngine
    )
    
    # Generators
    from .generators import DDRGenerator
    
    # Utils
    from .utils import validate_report_completeness
    
    # Schemas
    from .schemas import DDRReport
    
    # Config
    from .config import config
except ImportError:
    # Fallback for direct execution
    from extractors import InspectionParser, ThermalParser
    from processors import (
        DataStructurer,
        Deduplicator,
        CorrelationEngine,
        SeverityEngine
    )
    from generators import DDRGenerator
    from utils import validate_report_completeness
    from schemas import DDRReport
    from config import config


class DDRPipeline:
    """Main pipeline for DDR generation"""
    
    def __init__(
        self,
        llm_provider: Optional[str] = None,
        enable_deduplication: bool = True
    ):
        """
        Initialize DDR pipeline
        
        Args:
            llm_provider: LLM provider ("openai", "gemini", "ollama")
            enable_deduplication: Whether to deduplicate findings
        """
        self.structurer = DataStructurer()
        self.deduplicator = Deduplicator() if enable_deduplication else None
        self.correlator = CorrelationEngine()
        self.severity_engine = SeverityEngine()
        self.generator = DDRGenerator(llm_provider)
        self.enable_deduplication = enable_deduplication
    
    def process(
        self,
        inspection_pdf_path: str,
        thermal_pdf_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> DDRReport:
        """
        Process PDFs and generate DDR report
        
        Args:
            inspection_pdf_path: Path to inspection report PDF
            thermal_pdf_path: Path to thermal report PDF (optional)
            output_dir: Output directory for reports (optional)
            
        Returns:
            Complete DDR report
        """
        print("="*60)
        print("DDR GENERATION PIPELINE")
        print("="*60)
        
        # Step 1: Extract data from PDFs
        print("\n[1/7] Extracting data from inspection report...")
        inspection_result = self._extract_inspection_data(inspection_pdf_path)
        print(f"     ✓ Found {len(inspection_result.raw_negative_findings)} area(s) with issues")
        
        thermal_data = {}
        if thermal_pdf_path:
            print("\n[2/7] Extracting thermal data...")
            thermal_data = self._extract_thermal_data(thermal_pdf_path)
            print(f"     ✓ Found thermal data for {len(thermal_data)} area(s)")
        else:
            print("\n[2/7] Skipping thermal data (no thermal PDF provided)")
        
        # Step 2: Structure data
        print("\n[3/7] Structuring data...")
        report = self.structurer.structure_data(inspection_result, thermal_data)
        report = self.structurer.merge_similar_areas(report)
        print(f"     ✓ Structured {len(report.areas)} unique area(s)")
        
        # Step 3: Deduplicate findings
        if self.enable_deduplication and self.deduplicator:
            print("\n[4/7] Deduplicating findings...")
            report = self._deduplicate_report(report)
            print("     ✓ Deduplication complete")
        else:
            print("\n[4/7] Skipping deduplication")
        
        # Step 4: Correlation analysis
        print("\n[5/7] Performing correlation analysis...")
        report.correlation_result = self.correlator.correlate(report)
        print(f"     ✓ Identified {len(report.correlation_result.root_causes)} root cause(s)")
        
        # Step 5: Severity assessment
        print("\n[6/7] Assessing severity...")
        report.severity_assessment = self.severity_engine.assess_severity(report)
        print(f"     ✓ Overall severity: {report.severity_assessment.overall_severity}")
        
        # Step 6: Generate report sections with LLM
        print("\n[7/7] Generating report sections with LLM...")
        report = self.generator.generate_report(report)
        print("     ✓ Report generation complete")
        
        # Validate report
        print("\n" + "="*60)
        validation = validate_report_completeness(report)
        print(f"Report Quality Score: {validation['score']}/1.0")
        
        if validation['warnings']:
            print("\nWarnings:")
            for warning in validation['warnings']:
                print(f"  ⚠ {warning}")
        
        if validation['issues']:
            print("\nIssues:")
            for issue in validation['issues']:
                print(f"  ✗ {issue}")
        
        # Export reports
        if output_dir:
            self._export_reports(report, output_dir, inspection_pdf_path)
        
        print("\n" + "="*60)
        print("PIPELINE COMPLETE")
        print("="*60)
        
        return report
    
    def _extract_inspection_data(self, pdf_path: str):
        """Extract data from inspection PDF"""
        with InspectionParser(pdf_path) as parser:
            return parser.parse()
    
    def _extract_thermal_data(self, pdf_path: str):
        """Extract data from thermal PDF"""
        with ThermalParser(pdf_path) as parser:
            return parser.parse()
    
    def _deduplicate_report(self, report: DDRReport) -> DDRReport:
        """Apply deduplication to all findings in report"""
        for area in report.areas:
            area.negative_findings = self.deduplicator.deduplicate_findings(
                area.negative_findings
            )
            area.positive_findings = self.deduplicator.deduplicate_findings(
                area.positive_findings
            )
        return report
    
    def _export_reports(self, report: DDRReport, output_dir: str, inspection_path: str):
        """Export reports to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(inspection_path).stem
        
        # Export markdown
        md_path = output_path / f"{base_name}_DDR_{timestamp}.md"
        self.generator.export_to_markdown(report, str(md_path))
        
        # Export JSON
        json_path = output_path / f"{base_name}_DDR_{timestamp}.json"
        self.generator.export_to_json(report, str(json_path))


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate Detailed Diagnostic Reports from inspection PDFs"
    )
    parser.add_argument(
        "--inspection",
        required=True,
        help="Path to inspection report PDF"
    )
    parser.add_argument(
        "--thermal",
        help="Path to thermal report PDF (optional)"
    )
    parser.add_argument(
        "--output",
        default=str(config.paths.output_dir),
        help="Output directory for reports"
    )
    parser.add_argument(
        "--llm",
        choices=["openai", "gemini", "ollama"],
        default=config.api.llm_provider,
        help="LLM provider to use"
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable deduplication"
    )
    
    args = parser.parse_args()
    
    # Validate config
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease set up your API keys:")
        print("  - For OpenAI: set OPENAI_API_KEY environment variable")
        print("  - For Gemini: set GEMINI_API_KEY environment variable")
        print("  - For Ollama: ensure Ollama is running locally")
        return
    
    # Create pipeline
    pipeline = DDRPipeline(
        llm_provider=args.llm,
        enable_deduplication=not args.no_dedup
    )
    
    # Process reports
    try:
        report = pipeline.process(
            inspection_pdf_path=args.inspection,
            thermal_pdf_path=args.thermal,
            output_dir=args.output
        )
        print(f"\n✓ Successfully generated DDR report")
        print(f"  Severity: {report.severity_assessment.overall_severity}")
        print(f"  Areas analyzed: {len(report.areas)}")
        print(f"  Root causes: {len(report.correlation_result.root_causes)}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
