"""
Example usage of DDR generation system.
Demonstrates end-to-end workflow.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ddr_generator.main import DDRPipeline
from ddr_generator.config import config


def example_basic_usage():
    """Basic usage example with inspection report only"""
    print("Example 1: Basic Usage (Inspection Only)\n")
    print("="*60)
    
    # Initialize pipeline with Gemini (or change to "openai" or "ollama")
    pipeline = DDRPipeline(llm_provider="gemini")
    
    # Process inspection report
    # Note: Replace with actual PDF paths
    inspection_pdf = "data/samples/inspection_report.pdf"
    
    # Check if file exists
    if not Path(inspection_pdf).exists():
       print(f"⚠ Sample file not found: {inspection_pdf}")
        print("Please add your inspection PDF to ddr_generator/data/samples/")
        return None
    
    report = pipeline.process(
        inspection_pdf_path=inspection_pdf,
        output_dir=str(config.paths.output_dir)
    )
    
    print(f"\n✓ Report generated successfully!")
    return report


def example_with_thermal():
    """Example with both inspection and thermal reports"""
    print("\n\nExample 2: With Thermal Data\n")
    print("="*60)
    
    pipeline = DDRPipeline(llm_provider="gemini")
    
    inspection_pdf = "data/samples/inspection_report.pdf"
    thermal_pdf = "data/samples/thermal_report.pdf"
    
    # Check if files exist
    if not Path(inspection_pdf).exists():
        print(f"⚠ Sample file not found: {inspection_pdf}")
        return None
    
    if not Path(thermal_pdf).exists():
        print(f"⚠ Thermal file not found: {thermal_pdf}")
        print("Proceeding with inspection only...")
        thermal_pdf = None
    
    report = pipeline.process(
        inspection_pdf_path=inspection_pdf,
        thermal_pdf_path=thermal_pdf,
        output_dir=str(config.paths.output_dir)        )
    
    print(f"\n✓ Report generated successfully!")
    return report


def example_custom_output():
    """Example with custom output location"""
    print("\n\nExample 3: Custom Output Location\n")
    print("="*60)
    
    pipeline = DDRPipeline(llm_provider="gemini")
    
    inspection_pdf = "data/samples/inspection_report.pdf"
    custom_output = "output/my_reports"
    
    if not Path(inspection_pdf).exists():
        print(f"⚠ Sample file not found: {inspection_pdf}")
        return None
    
    report = pipeline.process(
        inspection_pdf_path=inspection_pdf,
        output_dir=custom_output
    )
    
    print(f"\n✓ Reports saved to: {custom_output}")
    return report


def example_no_deduplication():
    """Example with deduplication disabled"""
    print("\n\nExample 4: Without Deduplication\n")
    print("="*60)
    
    # Disable deduplication (keeps all findings as-is)
    pipeline = DDRPipeline(
        llm_provider="gemini",
        enable_deduplication=False
    )
    
    inspection_pdf = "data/samples/inspection_report.pdf"
    
    if not Path(inspection_pdf).exists():
        print(f"⚠ Sample file not found: {inspection_pdf}")
        return None
    
    report = pipeline.process(
        inspection_pdf_path=inspection_pdf
    )
    
    print(f"\n✓ Report generated (duplicates preserved)")
    return report


def example_accessing_report_data():
    """Example of accessing structured report data"""
    print("\n\nExample 5: Accessing Report Data\n")
    print("="*60)
    
    pipeline = DDRPipeline(llm_provider="gemini")
    
    inspection_pdf = "data/samples/inspection_report.pdf"
    
    if not Path(inspection_pdf).exists():
        print(f"⚠ Sample file not found: {inspection_pdf}")
        return
    
    report = pipeline.process(inspection_pdf_path=inspection_pdf)
    
    # Access structured data
    print("\n" + "="*60)
    print("REPORT DATA SUMMARY")
    print("="*60)
    
    print(f"\nProperty: {report.property_details.address or 'Not Available'}")
    print(f"Inspection Date: {report.property_details.inspection_date or 'Not Available'}")
    
    print(f"\n--- Areas Affected ({len(report.areas)}) ---")
    for area in report.areas:
        if area.has_issues():
            print(f"\n{area.area_name}:")
            print(f"  Severity: {area.severity}")
            print(f"  Issues: {len(area.negative_findings)}")
            print(f"  Causes: {len(area.positive_findings)}")
            if area.thermal_evidence:
                print(f"  Thermal: {area.thermal_evidence.summary()}")
    
    if report.correlation_result:
        print(f"\n--- Root Causes ({len(report.correlation_result.root_causes)}) ---")
        for i, cause in enumerate(report.correlation_result.root_causes, 1):
            print(f"{i}. {cause.cause_description}")
            print(f"   Confidence: {cause.confidence}")
    
    if report.severity_assessment:
        print(f"\n--- Severity Assessment ---")
        print(f"Overall: {report.severity_assessment.overall_severity}")
        print(f"Score: {report.severity_assessment.severity_score}/1.0")
        print(f"High Priority: {len(report.severity_assessment.high_priority_areas)} area(s)")
        print(f"Medium Priority: {len(report.severity_assessment.medium_priority_areas)} area(s)")
        print(f"Low Priority: {len(report.severity_assessment.low_priority_areas)} area(s)")


if __name__ == "__main__":
    print("DDR GENERATION SYSTEM - EXAMPLES\n")
    
    # Run examples
    # Uncomment the example you want to run
    
    # example_basic_usage()
    # example_with_thermal()
    # example_custom_output()
    # example_no_deduplication()
    example_accessing_report_data()
    
    print("\n" + "="*60)
    print("Examples complete!")
    print("="*60)
