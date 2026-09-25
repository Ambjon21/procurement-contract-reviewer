import streamlit as st
import openai
import json
import pypdf

st.set_page_config(page_title="Contract Term Reviewer & Risk Analysis", layout="wide")

st.title("Contract Term & Risk Analysis Tool")
st.write("Automated non-standard clause extraction and risk categorization for procurement contracts.")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter OpenAI API Key:", type="password")

def analyze_contract(text, api_key):
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""
    You are an enterprise procurement contract risk analysis engine.
    Analyze the following contract text and identify key terms, non-standard clauses, and potential risks.

    Extract into a valid JSON object with the following keys:
    - "contract_title": Title or nature of agreement (string)
    - "parties": Primary parties involved (string)
    - "payment_terms": Payment terms summary e.g., Net 30, Net 60 (string)
    - "governing_law": State/jurisdiction (string)
    - "overall_risk_level": Exactly ONE of ["HIGH", "MEDIUM", "LOW"]
    - "flagged_risks": Array of objects, each containing:
        - "clause_type": e.g., Indemnification, Payment Terms, Termination, Liability (string)
        - "risk_level": Exactly ONE of ["HIGH", "MEDIUM", "LOW"]
        - "finding": Summary of the non-standard term or issue (string)
        - "recommendation": Recommended negotiation redline or fallback position (string)

    Contract Text:
    {text}

    Respond ONLY with a raw JSON object. Do not use markdown code block formatting.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You output strict raw JSON objects only."},
                  {"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    return json.loads(response.choices[0].message.content.strip())

# Input Method Selection
input_type = st.radio("Select Input Source:", ["Paste Contract Text", "Upload Contract PDF"])

raw_text = ""

if input_type == "Paste Contract Text":
    raw_text = st.text_area("Paste Contract Text or Clause:", height=250, 
                            placeholder="Paste full agreement text or specific contract clauses here...")
else:
    uploaded_file = st.file_uploader("Upload Contract PDF", type=["pdf"])
    if uploaded_file:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            raw_text += page.extract_text() or ""

if st.button("Analyze Contract Terms"):
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
    elif not raw_text.strip():
        st.warning("Please provide contract text or upload a PDF document.")
    else:
        with st.spinner("Analyzing contract text for non-standard terms..."):
            try:
                result = analyze_contract(raw_text, api_key)
                
                st.subheader("Contract Summary")
                st.write(f"**Title:** {result.get('contract_title', 'N/A')}")
                st.write(f"**Parties:** {result.get('parties', 'N/A')}")
                st.write(f"**Payment Terms:** {result.get('payment_terms', 'N/A')}")
                st.write(f"**Governing Law:** {result.get('governing_law', 'N/A')}")
                
                # Overall Risk Banner
                overall_risk = result.get("overall_risk_level", "LOW")
                st.subheader("Overall Risk Level")
                if overall_risk == "HIGH":
                    st.error("HIGH RISK: Multiple non-standard or unfavorable terms detected requiring legal review.")
                elif overall_risk == "MEDIUM":
                    st.warning("MEDIUM RISK: Specific clauses require negotiation or buyer approval.")
                else:
                    st.success("LOW RISK: Terms align with standard procurement guidelines.")
                
                # Flagged Risks Detail
                st.subheader("Clause-by-Clause Risk Analysis")
                risks = result.get("flagged_risks", [])
                
                if not risks:
                    st.success("No high-risk clauses identified.")
                else:
                    for item in risks:
                        level = item.get("risk_level", "LOW")
                        clause = item.get("clause_type", "General")
                        finding = item.get("finding", "")
                        recommendation = item.get("recommendation", "")
                        
                        content = f"**Clause:** {clause}\n\n**Finding:** {finding}\n\n**Recommendation:** {recommendation}"
                        
                        if level == "HIGH":
                            st.error(content)
                        elif level == "MEDIUM":
                            st.warning(content)
                        else:
                            st.info(content)

            except Exception as e:
                st.error(f"Error processing contract document: {e}")
