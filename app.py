import streamlit as st
import openai
import base64
import json

# --- PAGE CONFIG ---
st.set_page_config(page_title="Claim Processing Helper", layout="wide")

# --- SECURE API KEY HANDLING ---
# You can also set this in Streamlit Cloud Secrets as OPENAI_API_KEY
st.sidebar.title("🔐 Access Control")
api_key_input = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if not api_key_input:
    st.info("Please enter your API Key to unlock the system.")
    st.stop()

client = openai.OpenAI(api_key=api_key_input)

# --- SYSTEM LOGIC (THE BRAIN) ---
st.sidebar.divider()
st.sidebar.subheader("📝 Customizable Logic Rules")
user_rules = st.sidebar.text_area("Update Logic Here:", 
    value="1. Engine/Chassis match must be exact.\n"
          "2. Check if Invoice Amount is less than Estimate.\n"
          "3. Verify if Vahan status is 'ACTIVE'.\n"
          "4. Claim > 1 Lakh requires RI report flag.", 
    height=150)

# --- UTILITY: IMAGE PROCESSING ---
def encode_image(file):
    return base64.b64encode(file.getvalue()).decode('utf-8')

# --- CORE FUNCTION: AI ANALYSIS ---
def process_claim_documents(files, logic):
    messages = [
        {
            "role": "system",
            "content": f"""You are a specialized Insurance Claim Auditor. 
            Analyze the documents provided and extract data to fill a specific checklist.
            
            RULES TO CHECK:
            {logic}
            
            OUTPUT FORMAT: 
            Return ONLY a JSON object with these keys: 
            'policy_info' (dict), 'tracker_info' (dict), 'rc_dl_info' (dict), 'financials' (dict), 'logic_results' (list of dicts with 'rule' and 'status')."""
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract all data from these claim documents. Compare RC vs Policy for Engine/Chassis. Compare Invoice vs Estimate vs Assessment. Generate the checklist data."}
            ]
        }
    ]

    for file in files:
        b64_img = encode_image(file)
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:{file.type};base64,{b64_img}"}
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=3000
    )
    return json.loads(response.choices[0].message.content)

# --- UI LAYOUT ---
st.title("🚗 Claim Genuineness Assistant")
st.write("Upload all screenshots and documents to verify the claim against the checklist.")

uploaded_docs = st.file_uploader(
    "Upload Policy, RC, DL, FSR, Invoice, Vahan/IIB Screenshots", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg']
)

if st.button("🔍 Run Audit & Generate Checklist"):
    if not uploaded_docs:
        st.warning("Please upload files first.")
    else:
        with st.spinner("Analyzing cross-document data..."):
            try:
                results = process_claim_documents(uploaded_docs, user_rules)
                
                # --- DISPLAY RESULTS (THE CHECKLIST) ---
                st.success("Analysis Complete")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 Policy & Tracker Particulars")
                    st.json(results.get('policy_info', {}))
                    st.json(results.get('tracker_info', {}))
                
                with col2:
                    st.subheader("📄 RC & Driving License")
                    st.json(results.get('rc_dl_info', {}))
                
                st.divider()
                st.subheader("💰 Financial Validation")
                f = results.get('financials', {})
                st.write(f"**Estimate:** {f.get('estimate')}")
                st.write(f"**Invoice:** {f.get('invoice')}")
                st.write(f"**Assessment:** {f.get('assessment')}")
                
                # Logic Visualizer
                st.subheader("⚖️ Brain Logic Check")
                for rule in results.get('logic_results', []):
                    icon = "✅" if "pass" in rule['status'].lower() or "yes" in rule['status'].lower() else "❌"
                    st.write(f"{icon} **{rule['rule']}**: {rule['status']}")

            except Exception as e:
                st.error(f"Error processing: {e}")
