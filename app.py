import streamlit as st
import google.generativeai as genai
import PIL.Image
import fitz  # PyMuPDF
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Claim Assistant (Free)", layout="wide")

# --- HARDCODED API KEY ---
GEMINI_FREE_KEY = "PASTE_YOUR_GEMINI_KEY_HERE"

# Configure the AI
genai.configure(api_key=GEMINI_FREE_KEY)

# We use the specific version name to avoid the 404 error
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# --- SYSTEM LOGIC ---
st.sidebar.title("🧠 Claim Logic")
default_rules = """
1. ENGINE & CHASSIS: Must match exactly between RC and Policy.
2. VAHAN STATUS: Must be 'ACTIVE' in the screenshot provided.
3. NCB: Check if NCB recovery is required based on IIB screenshot.
4. FINANCIALS: Surveyor Assessment must be <= Estimate and >= Invoice.
5. DL: Driver name on Driving License must match the Claim Form.
"""
user_rules = st.sidebar.text_area("Edit Logic Rules:", value=default_rules, height=300)

# --- PDF TO IMAGE CONVERSION ---
def convert_pdf_to_images(uploaded_file):
    images = []
    pdf_data = uploaded_file.read()
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

# --- MAIN UI ---
st.title("🚗 Claim Genuineness Helper")

uploaded_docs = st.file_uploader(
    "Upload Policy, RC, DL, FSR, Invoice, Screenshots", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg', 'pdf']
)

if st.button("🚀 Run Audit"):
    if not uploaded_docs:
        st.warning("Please upload files first.")
    elif GEMINI_FREE_KEY == "PASTE_YOUR_GEMINI_KEY_HERE":
        st.error("Please paste your Gemini API Key in the code!")
    else:
        with st.spinner("Analyzing documents for free..."):
            try:
                all_attachments = []
                for file in uploaded_docs:
                    if file.type == "application/pdf":
                        all_attachments.extend(convert_pdf_to_images(file))
                    else:
                        all_attachments.append(PIL.Image.open(file))

                # If there are too many pages/images, the free tier might complain.
                # Limiting to 15 items for stability.
                if len(all_attachments) > 15:
                    st.warning("Large number of pages detected. Processing the first 15 pages only.")
                    all_attachments = all_attachments[:15]

                prompt = f"""
                Analyze these insurance documents. Extract data and verify these rules:
                {user_rules}
                
                Generate a 'DOCUMENTS CHECKLIST' table and a final 'GENUINENESS VERDICT'.
                """

                # Call the model
                response = model.generate_content([prompt] + all_attachments)
                
                st.success("Analysis Complete")
                st.divider()
                st.markdown(response.text)

            except Exception as e:
                st.error(f"Error: {e}")
                if "404" in str(e):
                    st.info("Check if your Gemini API key is valid and the 'google-generativeai' library is updated.")
