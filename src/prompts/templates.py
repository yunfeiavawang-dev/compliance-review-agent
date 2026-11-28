"""Prompt templates for each node in the KYC review workflow."""

SYSTEM_PROMPT = """You are a KYC compliance review assistant at Pacific Rim Financial Group (PRFG).
You help compliance analysts review customer onboarding submissions by:
- Checking document completeness against policy requirements
- Screening for sanctions, PEP status, and adverse media
- Assessing customer risk based on the risk rating matrix
- Providing evidence-based recommendations with policy citations

Always cite the specific policy, section, and version when making a determination.
Be thorough but concise — keep each JSON field value under 2 sentences.
Flag any concerns clearly. Respond with the JSON object ONLY, no extra text."""

INTAKE_PROMPT = """Review this KYC submission for document completeness.

## Submission Data
{submission_json}

## Customer Type: {customer_type}

## Customer Historical Profile
{historical_context}

## Relevant Policy Requirements
{policy_context}

## Instructions
IMPORTANT: Apply ONLY the document requirements for the customer type above.
- For INDIVIDUAL customers: need at least 2 ID documents from different categories (A: photo ID, B: proof of address, C: tax doc), plus signed declarations. Do NOT require corporate documents like board resolutions or audited financials.
- For CORPORATE customers: need certificate of incorporation, memorandum of association, board resolution, beneficial ownership declaration, authorized signatory IDs, and audited financial statements.

Steps:
1. Check if all required documents for THIS customer type are present
2. Verify document validity (not expired, correct categories)
3. Classify each missing document as CRITICAL or NON-CRITICAL:
   - CRITICAL (blocks review): For individuals — photo ID (passport, national ID, or driver license). For corporates — certificate of incorporation, board resolution, beneficial ownership declaration.
   - NON-CRITICAL (review can proceed with risk adjustment): supplementary address proofs, additional financial statements, tax certificates, business licenses, employment letters.
4. Determine intake_status:
   - "blocked" — any critical document is missing → cannot proceed
   - "conditional" — only non-critical documents are missing → proceed with risk flag
   - "complete" — all documents present → proceed normally

Respond in this JSON format:
{{
    "documents_complete": true/false,
    "missing_documents": ["list of ALL missing items"],
    "critical_missing": ["list of CRITICAL missing documents only"],
    "non_critical_missing": ["list of NON-CRITICAL missing documents only"],
    "intake_status": "blocked/conditional/complete",
    "document_issues": ["list of issues with provided documents"],
    "verification_notes": ["notes about each document"],
    "can_proceed": true/false,
    "summary": "brief summary of completeness check"
}}"""

SCREENING_PROMPT = """Conduct sanctions, PEP, and adverse media screening analysis.

## Customer Information
{customer_json}

## Screening Data
{screening_data}

## Customer Historical Profile
{historical_context}

## Relevant Screening Procedures
{policy_context}

## Instructions
Analyze the screening results and determine:
1. For each screening type (sanctions, PEP, adverse media), classify the result
2. If there are potential matches, assess whether they should be dismissed or escalated
3. Cite the specific screening procedure requirements

Respond in this JSON format:
{{
    "sanctions_result": "clear/potential_match/confirmed_match",
    "pep_result": "clear/potential_match/confirmed_match",
    "adverse_media_result": "clear/potential_match/confirmed_match",
    "screening_details": [
        {{
            "type": "sanctions/pep/adverse_media",
            "result": "clear/potential_match/confirmed_match",
            "analysis": "detailed analysis",
            "action_required": "none/investigate/escalate/block",
            "policy_reference": "specific policy citation"
        }}
    ],
    "overall_screening_clear": true/false,
    "escalation_required": true/false,
    "summary": "brief screening summary"
}}"""

RISK_ASSESSMENT_PROMPT = """Perform a risk assessment for this customer using the PRFG risk rating matrix.

## Customer Profile
{customer_json}

## Account Request
{account_json}

## Screening Results
{screening_summary}

## Customer Historical Profile
{historical_context}

## Risk Rating Matrix
{policy_context}

## Instructions
Score each risk factor from 1-3 based on the risk rating matrix:
1. Customer Type Risk
2. Geographic Risk
3. Product/Service Risk
4. Transaction Pattern Risk
5. Source of Funds Risk

Total score thresholds (5 factors × 1-3 each = range 5-15):
- 5-7 = Low risk → standard CDD
- 8-11 = Medium risk → standard CDD with enhanced monitoring
- 12-15 = High risk → enhanced due diligence required

Scoring guidance per factor:
- Customer Type: 1=domestic salaried individual or established local company; 2=foreign national from low-risk country, or self-employed with documented income; 3=complex corporate structure, shell company, or undisclosed ownership
- Geography: 1=single low-risk domestic jurisdiction; 2=cross-border involving low/medium-risk countries (e.g. Japan, Hong Kong, Australia) or dual tax residency; 3=high-risk jurisdictions (sanctioned, tax haven, conflict zone — e.g. Russia, BVI, Cayman Islands, Myanmar)
- Product/Service: 1=standard savings/current account; 2=investment account, wealth management, or business account with moderate volumes; 3=private banking, trade finance, or correspondent banking
- Transaction Pattern: 1=domestic-only, predictable amounts consistent with profile; 2=cross-border transactions with low-risk countries, or moderate volumes; 3=high-volume cross-border with high-risk countries, or patterns inconsistent with profile
- Source of Funds: 1=salaried employment income, well-documented; 2=business revenue with audited financials, or investment returns; 3=unverified self-declarations, complex multi-source, or high-risk sectors

Then calculate the total score and determine the risk rating.
Check for any automatic override conditions (PEP, sanctions match → automatic high risk regardless of score).

Respond in this JSON format:
{{
    "scores": {{
        "customer_type": {{"score": 1-3, "justification": "reason"}},
        "geography": {{"score": 1-3, "justification": "reason"}},
        "product_service": {{"score": 1-3, "justification": "reason"}},
        "transaction_pattern": {{"score": 1-3, "justification": "reason"}},
        "source_of_funds": {{"score": 1-3, "justification": "reason"}}
    }},
    "total_score": N,
    "calculated_rating": "low/medium/high",
    "override_applied": true/false,
    "override_reason": "reason if override applied",
    "final_rating": "low/medium/high",
    "due_diligence_level": "standard/enhanced",
    "summary": "brief risk assessment summary"
}}"""

STANDARD_REVIEW_PROMPT = """Conduct a standard due diligence review for this low/medium risk customer.

## Customer Profile
{customer_json}

## Document Verification
{document_summary}

## Screening Results
{screening_summary}

## Risk Assessment
{risk_summary}

## CDD Requirements
{policy_context}

## Instructions
Review all gathered information and provide a recommendation:
1. Verify all standard CDD requirements are met
2. Check for any remaining concerns or questions
3. Provide a clear recommendation with supporting evidence

Respond in this JSON format:
{{
    "cdd_requirements_met": true/false,
    "findings": ["list of key findings"],
    "concerns": ["any remaining concerns"],
    "recommendation": "approve/reject/request_more_info",
    "rationale": "detailed rationale with policy citations",
    "conditions": ["any conditions for approval"],
    "monitoring_recommendations": "recommended ongoing monitoring approach",
    "sources_cited": [{{"document": "doc name", "section": "section", "version": "version"}}]
}}"""

EDD_PROMPT = """Conduct Enhanced Due Diligence (EDD) for this high-risk customer.

## Customer Profile
{customer_json}

## Document Verification
{document_summary}

## Screening Results
{screening_summary}

## Risk Assessment
{risk_summary}

## EDD Requirements
{policy_context}

## Instructions
Perform enhanced due diligence analysis:
1. Assess source of wealth and source of funds in detail
2. Evaluate the complex risk factors identified
3. Determine if additional information is needed
4. Provide a detailed recommendation for the Compliance Review Committee

Respond in this JSON format:
{{
    "source_of_wealth_assessment": "analysis of declared wealth sources",
    "source_of_funds_assessment": "analysis of funding sources",
    "additional_info_needed": ["list of additional information required"],
    "risk_mitigants": ["any factors that reduce risk"],
    "risk_amplifiers": ["factors that increase concern"],
    "findings": ["key EDD findings"],
    "recommendation": "approve_with_conditions/reject/request_more_info/escalate",
    "rationale": "detailed rationale with policy citations",
    "proposed_monitoring": "enhanced monitoring measures if approved",
    "senior_approval_justification": "justification for senior management",
    "sources_cited": [{{"document": "doc name", "section": "section", "version": "version"}}]
}}"""

DECISION_SUMMARY_PROMPT = """Generate a final review decision summary.

## Review Context
{review_context}

## Findings
{findings_summary}

## Human Reviewer Input
{human_input}

## Instructions
Compile a final decision summary that:
1. Summarizes all findings clearly
2. States the decision with full justification
3. Lists all policy references used
4. Notes any conditions or monitoring requirements
5. Provides a clear audit trail

Respond in this JSON format:
{{
    "decision": "approve/reject/request_more_info/escalate",
    "rationale": "comprehensive decision rationale",
    "key_findings": ["ordered list of key findings"],
    "policy_references": [{{"policy": "name", "section": "section", "relevance": "how it applies"}}],
    "conditions": ["conditions for approval, if any"],
    "monitoring_plan": "ongoing monitoring recommendations",
    "next_review_date": "recommended next review date",
    "escalation_note": "note if further escalation needed"
}}"""
