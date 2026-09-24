import json
import streamlit as st
from pypdf import PdfReader
from openai import OpenAI

# Page Configuration
st.set_page_config(
    page_title="Procurement AI Contract Reviewer",
    page_icon="📜",
    layout="wide"
)

# Sidebar - Settings & API Key
st.sidebar.title("⚙️ Setup & Settings")
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

# Sidebar - Default Procurement Rulebook
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Procurement Rulebook")
default_rules = """1. Payment Terms: Must be Net 60 days or longer. Net 30 requires buyer approval.
2. Auto-Renewal: Automatic renewal clauses are strictly prohibited.
3. Liability Cap: Limitation of liability must be capped at 1x contract value or lower.
4. Governing Law: Must be governed by state laws of Delaware or Tennessee.
5. Termination Notice: Must allow termination for convenience with at least 30 days written notice."""

rulebook = st.sidebar.text_area("Approved Policy Rules", value=default_rules, height=220)

# Main App Header
st.title("📜 AI Contract Compliance & Risk Screener")
st.markdown("""
**Automated First Line of Defense:** Upload vendor agreements (PDF or TXT) to evaluate compliance against standard company procurement playbooks, flag high-risk clauses, and generate suggested redline revisions.
""")

st.markdown("---")

# Document Upload Section
col1, col2 = st.columns([1, 1])

contract_text = ""

with col1:
    st.subheader("1. Upload Contract Document")
    uploaded_file = st.file_uploader("Upload Vendor Agreement (PDF or TXT)", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    contract_text += text + "\n"
        else:
            contract_text = str(uploaded_file.read(), "utf-8")
            
        st.success(f"Successfully loaded: {uploaded_file.name} ({len(contract_text)} characters)")
        
        with st.expander("Preview Extracted Contract Text"):
            st.text_area("Raw Text", value=contract_text[:2000] + "...", height=200)

# Analysis Logic
with col2:
    st.subheader("2. Run Compliance Audit")
    st.info("The AI model will screen the contract against your Procurement Rulebook and generate structured risk flags.")
    
    run_analysis = st.button("🔍 Analyze Contract for Risks", type="primary", use_container_width=True)

if run_analysis:
    if not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar to run the analysis.")
    elif not contract_text:
        st.error("Please upload a contract document first.")
    else:
        with st.spinner("Analyzing contract against procurement rulebook..."):
            try:
                client = OpenAI(api_key=api_key)
                
                system_prompt = """You are an expert enterprise Procurement & Legal Operations Analyst.
Your task is to analyze contract text against a given Procurement Policy Rulebook.
Output your analysis strictly in valid JSON format with the following structure:
{
    "summary": "Brief 2-3 sentence overview of the agreement",
    "overall_risk": "Low" | "Medium" | "High",
    "evaluations": [
        {
            "rule_name": "Name of the rule being evaluated",
            "status": "Green" | "Yellow" | "Red",
            "found_clause": "Exact quote or excerpt from the contract, or 'Not Found'",
            "issue_description": "Explanation of compliance or violation",
            "suggested_redline": "Recommended alternative clause language for negotiation"
        }
    ]
}"""

                user_prompt = f"""Procurement Policy Rulebook:
{rulebook}

Contract Text:
{contract_text}"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )

                response_message = response.choices[0].message.content
                if response_message:
                    result = json.loads(response_message)
                else:
                    result = {}
                
                # Display Results
                st.markdown("---")
                st.header("📊 Compliance Risk Scorecard")
                
                summary_col, risk_col = st.columns([3, 1])
                with summary_col:
                    st.markdown(f"**Executive Summary:** {result.get('summary', 'N/A')}")
                with risk_col:
                    overall_risk = result.get('overall_risk', 'Medium')
                    if overall_risk == "High":
                        st.error(f"Overall Risk: {overall_risk}")
                    elif overall_risk == "Medium":
                        st.warning(f"Overall Risk: {overall_risk}")
                    else:
                        st.success(f"Overall Risk: {overall_risk}")

                st.subheader("Detailed Clause Evaluations")
                
                for item in result.get("evaluations", []):
                    status = item.get("status", "Yellow")
                    
                    if status == "Red":
                        badge = "🚨 RED FLAG (Non-Compliant)"
                    elif status == "Yellow":
                        badge = "⚠️ YELLOW FLAG (Needs Review)"
                    else:
                        badge = "✅ GREEN FLAG (Compliant)"
                        
                    with st.expander(f"{badge} — {item.get('rule_name', 'Rule')}"):
                        st.markdown("**Found Clause in Contract:**")
                        st.info(f'"{item.get("found_clause", "N/A")}"')
                        
                        st.markdown("**Analysis & Issue Description:**")
                        st.write(item.get("issue_description", "N/A"))
                        
                        if status in ["Red", "Yellow"] and item.get("suggested_redline"):
                            st.markdown("**Suggested Redline / Revision Language:**")
                            st.code(item.get("suggested_redline"), language="text")

            except Exception as e:
                st.error(f"An error occurred during analysis: {str(e)}")
