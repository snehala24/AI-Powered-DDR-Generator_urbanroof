"""
DDR Generator: LLM-controlled report generation with fact-checking.
Generates client-friendly reports from structured data.
"""

import os
from datetime import datetime
from typing import Optional
from ..schemas import DDRReport
from ..config import config
from . import templates


class DDRGenerator:
    """Generates final DDR report using LLM"""
    
    def __init__(self, llm_provider: Optional[str] = None):
        """
        Initialize DDR generator
        
        Args:
            llm_provider: "openai", "gemini", or "ollama" (defaults to config)
        """
        self.provider = llm_provider or config.api.llm_provider
        self.client = self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """Initialize the appropriate LLM client based on provider"""
        if self.provider == "openai":
            import openai
            openai.api_key = config.api.openai_api_key
            return openai
        
        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=config.api.gemini_api_key)
            return genai
        
        elif self.provider in ["ollama", "groq"]:
            # These providers use direct REST API calls, no client library needed
            return None
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def generate_report(self, report: DDRReport) -> DDRReport:
        """
        Generate complete DDR report using LLM
        
        Args:
            report: DDR report with structured data
            
        Returns:
            Report with all sections populated
        """
        print("Generating DDR report sections...")
        
        # Generate each section
        report.property_issue_summary = self._generate_property_summary(report)
        report.area_wise_observations = self._generate_area_observations(report)
        report.probable_root_cause = self._generate_root_cause_analysis(report)
        report.recommended_actions = self._generate_recommended_actions(report)
        report.additional_notes = self._generate_additional_notes(report)
        
        # Identify missing information
        report.missing_information = self._identify_missing_information(report)
        
        return report
    
    def _generate_property_summary(self, report: DDRReport) -> str:
        """Generate property issue summary section"""
        print("  - Generating property summary...")
        
        # Prepare data for prompt
        areas_list = ", ".join([area.area_name for area in report.areas if area.has_issues()])
        
        severity_info = ""
        if report.severity_assessment:
            severity_info = (
                f"{report.severity_assessment.overall_severity} "
                f"(Score: {report.severity_assessment.severity_score}/1.0)"
            )
        
        root_causes = ""
        if report.correlation_result and report.correlation_result.root_causes:
            root_causes = templates.format_root_causes(report.correlation_result.root_causes)
        
        prompt = templates.PROPERTY_SUMMARY_PROMPT.format(
            property_details=templates.format_property_details(report.property_details),
            num_areas=len([a for a in report.areas if a.has_issues()]),
            areas_list=areas_list or "Not Available",
            severity_info=severity_info or "Not Available",
            root_causes=root_causes or "Not Available"
        )
        
        return self._call_llm(prompt)
    
    def _generate_area_observations(self, report: DDRReport) -> str:
        """Generate area-wise observations section"""
        print("  - Generating area-wise observations...")
        
        area_data = templates.format_area_data(report.areas)
        
        prompt = templates.AREA_OBSERVATIONS_PROMPT.format(
            area_data=area_data
        )
        
        return self._call_llm(prompt)
    
    def _generate_root_cause_analysis(self, report: DDRReport) -> str:
        """Generate root cause analysis section"""
        print("  - Generating root cause analysis...")
        
        if not report.correlation_result:
            return "Not Available - Correlation analysis not performed"
        
        root_causes_data = templates.format_root_causes(report.correlation_result.root_causes)
        
        cross_area_text = ""
        if report.correlation_result.cross_area_links:
            for area, links in report.correlation_result.cross_area_links.items():
                cross_area_text += f"\n**{area}:**\n"
                for link in links:
                    # links are now strings, not dicts
                    cross_area_text += f"- {link}\n"
        
        conflicts_text = "\n".join(report.correlation_result.conflicts) if report.correlation_result.conflicts else "None"
        
        prompt = templates.ROOT_CAUSE_PROMPT.format(
            root_causes_data=root_causes_data or "No specific root causes identified",
            cross_area_links=cross_area_text or "No cross-area correlations found",
            conflicts=conflicts_text
        )
        
        return self._call_llm(prompt)
    
    def _generate_recommended_actions(self, report: DDRReport) -> str:
        """Generate recommended actions section"""
        print("  - Generating recommended actions...")
        
        if not report.severity_assessment:
            return "Not Available - Severity assessment not performed"
        
        sev = report.severity_assessment
        
        root_causes_summary = ""
        if report.correlation_result and report.correlation_result.root_causes:
            root_causes_summary = templates.format_root_causes(report.correlation_result.root_causes)
        
        prompt = templates.RECOMMENDED_ACTIONS_PROMPT.format(
            overall_severity=sev.overall_severity,
            high_priority=templates.format_priority_list(sev.high_priority_areas),
            medium_priority=templates.format_priority_list(sev.medium_priority_areas),
            low_priority=templates.format_priority_list(sev.low_priority_areas),
            root_causes=root_causes_summary or "No root causes identified"
        )
        
        return self._call_llm(prompt)
    
    def _generate_additional_notes(self, report: DDRReport) -> str:
        """Generate additional notes section"""
        notes = []
        
        # Add thermal imaging notes if available
        thermal_count = sum(1 for area in report.areas if area.thermal_evidence)
        if thermal_count > 0:
            notes.append(
                f"Thermal imaging was used in {thermal_count} area(s) to detect temperature anomalies "
                "indicating moisture presence."
            )
        
        # Add correlation notes
        if report.correlation_result and len(report.correlation_result.root_causes) > 0:
            notes.append(
                f"Cross-area analysis identified {len(report.correlation_result.root_causes)} "
                "probable root cause(s) linking multiple observations."
            )
        
        # Add data quality notes
        extraction_meta = getattr(report.property_details, 'extraction_metadata', None)
        if extraction_meta:
            method = extraction_meta.get('extraction_method', 'unknown')
            notes.append(f"Data extracted using {method}-based parsing.")
        
        if not notes:
            return "No additional notes."
        
        return "\n\n".join(notes)
    
    def _identify_missing_information(self, report: DDRReport) -> list:
        """Identify missing information in the report"""
        missing = []
        
        # Check property details
        if not report.property_details.address:
            missing.append("Property address")
        if not report.property_details.inspection_date:
            missing.append("Inspection date")
        if not report.property_details.inspector_name:
            missing.append("Inspector name")
        
        # Check for areas with no thermal data
        no_thermal = [area.area_name for area in report.areas if area.has_issues() and not area.thermal_evidence]
        if no_thermal:
            missing.append(f"Thermal imaging data for: {', '.join(no_thermal)}")
        
        # Check for conflicts
        if report.correlation_result and report.correlation_result.conflicts:
            missing.append(f"Conflicting information detected: {len(report.correlation_result.conflicts)} conflict(s)")
        
        return missing if missing else ["All key information available"]
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt and return response"""
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=config.api.openai_model,
                    messages=[
                        {"role": "system", "content": templates.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Low temperature for factual output
                    max_tokens=1500
                )
                return response.choices[0].message.content.strip()
            
            elif self.provider == "gemini":
                # Use direct REST API to bypass library version issues
                import requests
                
                api_key = config.api.gemini_api_key
                # Use gemini-pro on v1 endpoint (most compatible)
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
                
                # Include system instruction in the prompt
                full_prompt = f"{templates.SYSTEM_PROMPT}\n\n{prompt}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1500
                    }
                }
                
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            elif self.provider == "ollama":
                import requests
                response = requests.post(
                    f"{config.api.ollama_endpoint}/api/generate",
                    json={
                        "model": config.api.ollama_model,
                        "prompt": f"{templates.SYSTEM_PROMPT}\n\n{prompt}",
                        "stream": False,
                        "options": {
                            "temperature": 0.3
                        }
                    }
                )
                response.raise_for_status()
                return response.json()['response'].strip()
            
            elif self.provider == "groq":
                # Groq API (fast and reliable!)
                import requests
                
                api_key = config.api.groq_api_key
                url = "https://api.groq.com/openai/v1/chat/completions"
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": config.api.groq_model,
                    "messages": [
                        {"role": "system", "content": templates.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            print(f"Warning: LLM call failed: {e}")
            return f"[Error generating this section: {str(e)}]"
    
    def export_to_markdown(self, report: DDRReport, output_path: str):
        """Export report to markdown file"""
        # Format severity assessment
        severity_info = ""
        if report.severity_assessment:
            sev = report.severity_assessment
            severity_info = {
                "overall_severity": sev.overall_severity,
                "severity_score": sev.severity_score,
                "severity_reasoning": sev.reasoning,
                "high_priority_list": templates.format_priority_list(sev.high_priority_areas),
                "medium_priority_list": templates.format_priority_list(sev.medium_priority_areas),
                "low_priority_list": templates.format_priority_list(sev.low_priority_areas)
            }
        else:
            severity_info = {
                "overall_severity": "Not Available",
                "severity_score": "N/A",
                "severity_reasoning": "Not Available",
                "high_priority_list": "Not Available",
                "medium_priority_list": "Not Available",
                "low_priority_list": "Not Available"
            }
        
        # Generate final report
        final_report = templates.DDR_REPORT_TEMPLATE.format(
            property_info=templates.format_property_details(report.property_details),
            property_summary=report.property_issue_summary or "Not Available",
            area_observations=report.area_wise_observations or "Not Available",
            root_cause_analysis=report.probable_root_cause or "Not Available",
            recommended_actions=report.recommended_actions or "Not Available",
            additional_notes=report.additional_notes or "Not Available",
            missing_information="\n".join([f"- {item}" for item in report.missing_information]),
            generation_timestamp=report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            **severity_info
        )
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
        
        print(f"\nReport exported to: {output_path}")
    
    def export_to_json(self, report: DDRReport, output_path: str):
        """Export report to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report.model_dump_json(indent=2))
        
        print(f"Structured data exported to: {output_path}")
