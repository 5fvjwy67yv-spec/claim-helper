import streamlit as st
import openai
import base64
import json
import fitz  # PyMuPDF to handle PDFs

# --- PAGE CONFIG ---
st.set_page_config(page_title="Claim Processing Helper", layout="wide")

st.sidebar.title("🔐 Access Control")
api_key_input = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if not api_key_input:
    st.info("Please enter your API Key in the sidebar to begin.")
    st.stop()

client = openai.OpenAI(api_key=api_key_input)

# --- SYSTEM LOGIC ---
st.sidebar.divider()
st.sidebar.subheader("📝 Customizable Logic Rules")
user_rules = st.sidebar.text_area("Update Logic Here:", 
    value="1. Engine/Chassis match must be exact.\n"
          "2. Check if Invoice Amount is less than Estimate.\n"
          "3. Verify if Vahan status is 'ACTIVE'.\n"
          "4. Claim > 1 Lakh requires RI report flag.", 
    height=150)

# --- UTILITY: PDF & IMAGE PROCESSING ---
def get_image_payloads(uploaded_file):
    """Converts images or PDF pages into base64 strings for the AI."""
    payloads = []
    
    if uploaded_file.type == "application/pdf":
        # Convert PDF pages to images
        pdf_data = uploaded_file.read()
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Higher resolution
            img_bytes = pix.tobytes("png")
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            payloads.append(f"data:image/png;base64,{base64_image}")
    else:
        # Standard image handling
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        payloads.append(f"data:{uploaded_file.type};base64,{base64_image}")
        
    return payloads

# --- CORE FUNCTION: AI ANALYSIS ---
def process_claim_documents(files, logic):
    messages = [
        {
            "role": "system",
            "content": f"""You are a specialized Insurance Claim Auditor. 
            Analyze the documents provided (Images and PDF pages).
            
            RULES TO CHECK:
            {logic}
            
            OUTPUT FORMAT: 
            Return ONLY a JSON object with these keys: 
            'policy_info' (dict), 'tracker_info' (dict), 'rc_dl_info' (dict), 'financials' (dict), 'logic_results' (list of dicts with 'rule' and 'status')."""
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": "Analyze these documents and check the rules."}]
        }
    ]

    for file in files:
        image_urls = get_image_payloads(file)
        for url in image_urls:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": url}
            })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=4000
    )
    return json.loads(response.choices[0].message.content)

# --- UI LAYOUT ---
st.title("🚗 Claim Genuineness Assistant")
st.write("Upload all documents (PDF or Images) to verify the claim.")

uploaded_docs = st.file_uploader(
    "Upload Policy, RC, DL, FSR, Invoice, Vahan Screenshots", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg', 'pdf'] # Added PDF here
)

if st.button("🔍 Run Audit & Generate Checklist"):
    if not uploaded_docs:
        st.warning("Please upload files first.")
    else:
        with st.spinner("Processing documents (this may take a minute for PDFs)..."):
            try:
                results = process_claim_documents(uploaded_docs, user_rules)
                
                st.success("Analysis Complete")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📋 Particulars")
                    st.write("**Policy/Tracker:**", results.get('policy_info'))
                    st.write("**RC/DL:**", results.get('rc_dl_info'))
                
                with col2:
                    st.subheader("💰 Financials")
                    st.json(results.get('financials'))
                
                st.divider()
                st.subheader("⚖️ Brain Logic Check")
                for rule in results.get('logic_results', []):
                    icon = "✅" if "pass" in rule['status'].lower() or "yes" in rule['status'].lower() else "❌"
                    st.write(f"{icon} **{rule['rule']}**: {rule['status']}")

            except Exception as e:
                st.error(f"Error: {e}")
