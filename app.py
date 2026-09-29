import streamlit as st
import openai
import json
import PyPDF2

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Contract Risk & Variance Analyzer",
    layout="wide"
)

# --- HELPER FUNCTION: EXTRACT TEXT FROM PDF OR TXT ---
def extract_text(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    else:
        return uploaded_file.read().decode("utf-8")

# --- SIDEBAR & API KEY SETUP ---
st.sidebar.header("⚙️ Configuration")
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("💡 About This Tool")
st.sidebar.info(
    "This app compares a company's standard purchasing terms against a vendor's proposed agreement, "
    "automatically highlighting unfavorable variances, financial liabilities, and high-risk terms."
)

# --- MAIN APP HEADER ---
st.title("Dual-Contract Risk & Variance Analyzer")
st.markdown(
    "Upload your **Company Standard Terms** alongside the **Vendor Proposal** to generate "
    "a side-by-side gap analysis and recommended counter-proposals."
)

# --- STEP 1: DUAL FILE UPLOADERS ---
st.subheader("1. Upload Contracts for Comparison")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Company Standard")
    company_file = st.file_uploader(
        "Upload Baseline Terms (PDF or TXT)", 
        type=["pdf", "txt"], 
        key="company_doc"
    )

with col2:
    st.markdown("### Vendor Proposal")
    vendor_file = st.file_uploader(
        "Upload Vendor Terms (PDF or TXT)", 
        type=["pdf", "txt"], 
        key="vendor_doc"
    )

# --- STEP 2: ANALYSIS & COMPARISON ENGINE ---
if company_file and vendor_file:
    st.success("✅ Both contracts uploaded successfully!")
    
    if st.button("🔍 Compare Contracts & Analyze Variances", type="primary"):
        if not api_key:
            st.error("⚠️ Please enter your OpenAI API Key in the sidebar to proceed.")
        else:
            with st.spinner("Extracting text and running risk variance analysis..."):
                try:
                    # Extract text from both files
                    company_text = extract_text(company_file)
                    vendor_text = extract_text(vendor_file)
                    
                    # Construct OpenAI API Client
                    client = openai.OpenAI(api_key=api_key)
                    
                    # System prompt for structured variance comparison
                    system_prompt = (
                        "You are an expert enterprise procurement specialist. You are provided with two contract documents:\n"
                        "DOCUMENT A: Company Standard Contract Terms\n"
                        "DOCUMENT B: Vendor Proposed Contract Terms\n\n"
                        "Task: Compare Document B against Document A. Identify any clauses where Document B deviates unfavorably "
                        "from Document A (e.g., Payment Terms, Restocking Fees, Limitation of Liability, Delivery Liabilities, Warranty).\n"
                        "Return the analysis strictly as a valid JSON object with a single key 'variances' containing an array of objects. "
                        "Each object must have the following keys:\n"
                        "- 'clause_category': (e.g., Payment Terms, Restocking Fee)\n"
                        "- 'company_standard': (e.g., Net 60, Max 10% fee)\n"
                        "- 'vendor_proposal': (e.g., Net 30, 25% fee)\n"
                        "- 'severity': ('High Risk', 'Medium Risk', 'Low Risk')\n"
                        "- 'recommendation': (Actionable advice or suggested counter-wording for negotiation)"
                    )
                    
                    user_prompt = f"--- DOCUMENT A (COMPANY STANDARD) ---\n{company_text[:4000]}\n\n--- DOCUMENT B (VENDOR PROPOSAL) ---\n{vendor_text[:4000]}"
                    
                    # Call OpenAI REST API
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2
                    )
                    
                    # Parse JSON response
                    result = json.loads(response.choices[0].message.content)
                    variances = result.get("variances", [])
                    
                    # --- STEP 3: DISPLAY METRIC CARDS & RESULTS ---
                    st.markdown("---")
                    st.subheader("2. Executive Summary Metrics")
                    
                    high_risk_count = sum(1 for v in variances if v.get("severity") == "High Risk")
                    med_risk_count = sum(1 for v in variances if v.get("severity") == "Medium Risk")
                    total_variances = len(variances)
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Variances Flagged", str(total_variances))
                    m2.metric("High-Risk Deviations", str(high_risk_count), delta=f"{high_risk_count} critical", delta_color="inverse")
                    m3.metric("Medium-Risk Deviations", str(med_risk_count))
                    
                    st.markdown("---")
                    st.subheader("3. Side-by-Side Clause Gap Analysis")
                    
                    # Display each flagged variance cleanly
                    for item in variances:
                        severity = item.get("severity", "Low Risk")
                        category = item.get("clause_category", "General Clause")
                        
                        if severity == "High Risk":
                            st.error(f"🔴 **{category}** — High Risk Variance")
                        elif severity == "Medium Risk":
                            st.warning(f"🟡 **{category}** — Medium Risk Variance")
                        else:
                            st.info(f"🔵 **{category}** — Low Risk / Informational")
                            
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Company Standard:** {item.get('company_standard')}")
                        with c2:
                            st.write(f"**Vendor Proposal:** {item.get('vendor_proposal')}")
                            
                        st.write(f" **Negotiation Advice:** {item.get('recommendation')}")
                        st.markdown("---")
                        
                except Exception as e:
                    st.error(f"An error occurred during analysis: {e}")

else:
    st.info("💡 Upload both documents above to activate the comparison engine.")
