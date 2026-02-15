"""
DDR report templates and prompts for LLM-based generation.
Defines structured templates for each report section.
"""


# System prompt for LLM
SYSTEM_PROMPT = """You are a structural diagnostic report generator for property inspections.

Your task is to convert structured technical data into clear, client-friendly language.

CRITICAL RULES:
1. Use ONLY the data provided to you - DO NOT invent facts
2. If information is missing, write "Not Available"
3. If you find conflicting information, explicitly mention the conflict
4. Use simple language that non-technical clients can understand
5. Avoid technical jargon unless necessary, and explain when used
6. Be precise and factual
7. Maintain professional tone

Your output should help property owners understand:
- What issues exist
- Where they are located
- What might be causing them
- How serious they are
- What actions to take
"""


# Section-specific prompts
PROPERTY_SUMMARY_PROMPT = """Generate a concise Property Issue Summary (2-3 paragraphs) based on this data:

Property Details:
{property_details}

Areas Affected ({num_areas}):
{areas_list}

Severity Assessment:
{severity_info}

Root Causes Identified:
{root_causes}

Create an executive summary that:
1. Introduces the property and inspection scope
2. Summarizes the main issues found
3. Highlights the most critical concerns
4. Sets context for detailed observations

Use client-friendly language. If any data is missing, write "Not Available" for that specific item."""


AREA_OBSERVATIONS_PROMPT = """Generate detailed Area-wise Observations based on this structured data:

{area_data}

For each area, provide:
1. Area name as heading
2. Issues found (negative observations)
3. Probable causes/sources identified (positive observations)
4. Thermal evidence if available
5. Overall assessment

Format as a structured markdown list with clear headings.
If thermal data shows cold zones, explain that this indicates moisture presence.
Use specific details from the data - do not generalize or add information not present.
If an area has no data, do not include it."""


ROOT_CAUSE_PROMPT = """Generate a Probable Root Cause Analysis based on this correlation data:

Identified Root Causes:
{root_causes_data}

Cross-Area Correlations:
{cross_area_links}

Conflicts Detected:
{conflicts}

Provide:
1. Main root causes with supporting evidence
2. How different areas are interconnected
3. Any conflicts or uncertainties in the data
4. Confidence level for each cause

Explain technical correlations in simple terms (e.g., "bathroom tile gaps allowing water to seep into adjacent room walls").
If conflicts exist, clearly state them as "Conflicting Information: [describe conflict]"."""


RECOMMENDED_ACTIONS_PROMPT = """Generate Recommended Actions based on severity assessment and root causes:

Severity Level: {overall_severity}

High Priority Areas:
{high_priority}

Medium Priority Areas:
{medium_priority}

Low Priority Areas:
{low_priority}

Root Causes:
{root_causes}

Provide prioritized recommendations:
1. **Immediate Actions** (for HIGH severity issues)
2. **Short-term Actions** (for MEDIUM severity issues)
3. **Monitoring** (for LOW severity issues)

Keep recommendations practical and specific to the issues found.
Include general advice like "Consult a licensed professional" where appropriate.
Do not recommend specific contractors or products."""


MISSING_INFO_PROMPT = """Review the following report data and identify any missing or unclear information:

{report_data_summary}

List any information that was:
1. Not available in source documents
2. Unclear or ambiguous
3. Conflicting between different sources

Be specific about what is missing. If everything is complete, write "All key information available"."""


# Template for final DDR report
DDR_REPORT_TEMPLATE = """# Detailed Diagnostic Report (DDR)

## Property Information
{property_info}

---

## 1. Property Issue Summary
{property_summary}

---

## 2. Area-wise Observations
{area_observations}

---

## 3. Probable Root Cause
{root_cause_analysis}

---

## 4. Severity Assessment
**Overall Severity:** {overall_severity}

**Assessment Score:** {severity_score}/1.0

**Reasoning:** {severity_reasoning}

### Priority Areas

**High Priority (Immediate Attention Required):**
{high_priority_list}

**Medium Priority (Short-term Action Needed):**
{medium_priority_list}

**Low Priority (Monitor):**
{low_priority_list}

---

## 5. Recommended Actions
{recommended_actions}

---

## 6. Additional Notes
{additional_notes}

---

## 7. Missing or Unclear Information
{missing_information}

---

**Report Generated:** {generation_timestamp}

*This report is based on inspection and thermal imaging data. For detailed remediation, please consult licensed professionals.*
"""


def format_property_details(property_details) -> str:
    """Format property details for display"""
    parts = []
    
    if property_details.address:
        parts.append(f"**Address:** {property_details.address}")
    else:
        parts.append("**Address:** Not Available")
    
    if property_details.inspection_date:
        parts.append(f"**Inspection Date:** {property_details.inspection_date}")
    
    if property_details.inspector_name:
        parts.append(f"**Inspector:** {property_details.inspector_name}")
    
    if property_details.property_id:
        parts.append(f"**Property ID:** {property_details.property_id}")
    
    return "\n".join(parts) if parts else "Not Available"


def format_area_data(areas) -> str:
    """Format area observations for LLM prompt"""
    formatted = []
    
    for area in areas:
        if not area.has_issues():
            continue
        
        area_text = f"\n### {area.area_name}\n"
        
        if area.negative_findings:
            area_text += "**Issues Found:**\n"
            for finding in area.negative_findings:
                area_text += f"- {finding}\n"
        
        if area.positive_findings:
            area_text += "**Probable Causes:**\n"
            for finding in area.positive_findings:
                area_text += f"- {finding}\n"
        
        if area.thermal_evidence:
            area_text += f"**Thermal Evidence:** {area.thermal_evidence.summary()}\n"
        
        if area.severity:
            area_text += f"**Severity:** {area.severity}\n"
        
        formatted.append(area_text)
    
    return "\n".join(formatted) if formatted else "No significant issues detected"


def format_root_causes(root_causes) -> str:
    """Format root causes for display"""
    if not root_causes:
        return "No root causes identified"
    
    formatted = []
    for i, cause in enumerate(root_causes, 1):
        cause_text = f"\n**{i}. {cause.cause_description}**\n"
        cause_text += f"- **Affected Areas:** {', '.join(cause.affected_areas)}\n"
        cause_text += f"- **Confidence:** {cause.confidence}\n"
        
        if cause.supporting_evidence:
            cause_text += "- **Evidence:**\n"
            for evidence in cause.supporting_evidence[:3]:  # Limit to top 3
                cause_text += f"  - {evidence}\n"
        
        formatted.append(cause_text)
    
    return "\n".join(formatted)


def format_priority_list(areas: list) -> str:
    """Format priority area list"""
    if not areas:
        return "None"
    
    return "\n".join([f"- {area}" for area in areas])
