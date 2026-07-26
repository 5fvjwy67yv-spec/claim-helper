import streamlit as st
import google.generativeai as genai
import PIL.Image
import fitz  # PyMuPDF
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Free Claim Assistant", layout="wide")

# --- API KEY HANDLING ---
# You can put your Gemini Key in Streamlit Secrets as GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Enter Google Gemini API Key", type="password")

if not api_key:
    st.info("Please enter your free Gemini API Key from Google AI Studio to begin.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- SYSTEM LOGIC ---
st.sidebar.divider()
st.sidebar.subheader("📝 Claim Rules")
user_rules = st.sidebar.text_area("Logic Rules:", 
    value="1. Exact Engine/Chassis match between RC and Policy.\n"
          "2. Invoice must not exceed Estimate.\n"
          "3. Vahan status must be ACTIVE.\n"
          "4. Driver name must match on DL and Claim Form.", 
    height=150)

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
st.title("🚗 Free Claim Genuineness Assistant")
st.write("Using Google Gemini Free Tier")

uploaded_docs = st.file_uploader(
    "Upload all documents (PDF/Images)", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg', 'pdf']
)

if st.button("🔍 Run Free Audit"):
    if not uploaded_docs:
        st.warning("Please upload files.")
    else:
        with st.spinner("Gemini is analyzing documents for free..."):
            try:
                # Prepare all images for Gemini
                all_attachments = []
                for file in uploaded_docs:
                    if file.type == "application/pdf":
                        all_attachments.extend(convert_pdf_to_images(file))
                    else:
                        all_attachments.append(PIL.Image.open(file))

                # Build the prompt
                prompt = f"""
                You are an Insurance Claim Expert. Analyze these document images.
                
                CHECK THESE RULES:
                {user_rules}
                
                TASK:
                1. Extract Policy No, Vehicle No, Engine No, Chassis No.
                2. Check if Engine/Chassis matches across documents.
                3. Check Vahan status from screenshots.
                4. Compare Estimate vs Invoice amounts.
                
                Provide a clear Checklist table and a 'Genuineness Verdict'.
                """

                # Send to Gemini
                response = model.generate_content([prompt] + all_attachments)
                
                st.success("Analysis Complete")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"Error: {e}")
