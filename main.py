import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor
import pypandoc
import plotly.express as px
import pandas as pd

# Environment variables
load_dotenv()

# Maximum number of workers for the ThreadPoolExecutor
max_workers = 10

# Initialize model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Functions
def get_gemini_response(input, image):
    response = model.generate_content([input, image[0]])
    return response.text

def pdf_to_images(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        images.append(pix.tobytes("png"))
    return images

def md_to_latex(md_content):
    latex_preamble = r"""\documentclass[a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{geometry}
\geometry{margin=1in}
\title{Digitalized Notes}
\author{}
\date{\today}
\begin{document}
\maketitle
"""
    latex_body = pypandoc.convert_text(md_content, 'latex', format='md')
    return latex_preamble + latex_body + "\end{document}"

def get_custom_prompt(format):
    base_prompt = (
        "You have to transcribe the handwritten notes in the image. The output should be structured "
        "with titles, chapters, paragraphs, and subparagraphs in the specified format."
    )
    return f"{base_prompt} Format: {format}."

def process_file():
    st.session_state.format_selected = (
        "Plain Text" if st.session_state.plain_text_convert
        else "Markdown" if st.session_state.markdown_convert
        else "LaTeX"
    )
    tasks = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, image_data in enumerate(st.session_state.images):
            image_parts = [{"mime_type": "image/png", "data": image_data}]
            tasks[i] = executor.submit(
                get_gemini_response, get_custom_prompt(st.session_state.format_selected), image_parts
            )
    st.session_state.output = "\n\n".join([task.result() for task in tasks.values()])

    if st.session_state.format_selected == "LaTeX":
        st.session_state.output = md_to_latex(st.session_state.output)

def generate_character_frequency(text):
    frequency = {}
    for char in text:
        if char.isalnum():
            frequency[char] = frequency.get(char, 0) + 1
    df = pd.DataFrame(list(frequency.items()), columns=['Character', 'Frequency'])
    return df.sort_values(by='Frequency', ascending=False)

# Initialize session state
def initialize_session_state():
    for key in ["uploaded_file", "plain_text_convert", "markdown_convert", "latex_convert", "images", "output", "format_selected"]:
        if key not in st.session_state:
            if key == "uploaded_file":
                st.session_state[key] = None
            elif key == "images":
                st.session_state[key] = []
            elif key == "format_selected":
                st.session_state[key] = ""  # Initialize format_selected as an empty string
            else:
                st.session_state[key] = ""

initialize_session_state()

# Interface settings
st.set_page_config(page_title="Handwritten Notes to Digital Notes", layout="wide", initial_sidebar_state="expanded")

# Modern design section
st.markdown(
    """
    <style>
    body {
        font-family: 'Arial', sans-serif;
        background: linear-gradient(to bottom right, #121212, #1e1e1e);
        color: #e0e0e0;
    }
    .stButton>button {
        background-color: #1db954;
        border: none;
        color: white;
        padding: 12px 24px;
        border-radius: 30px;
        font-size: 18px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #1ed760;
        transform: translateY(-3px);
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2);
    }
    .stTextArea {
        background-color: rgba(38, 50, 56, 0.9);
        border: 2px solid #37474f;
        border-radius: 12px;
        padding: 12px;
        color: #e0e0e0;
        font-size: 14px;
    }
    .stTextArea::placeholder {
        color: #9e9e9e;
    }
    .header {
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        color: #4caf50;
        margin-bottom: 20px;
    }
    .footer {
        text-align: center;
        font-size: 14px;
        color: #9e9e9e;
        margin-top: 40px;
    }
    .team-member {
        text-align: center;
        padding: 20px;
        background-color: #1e1e1e;
        border-radius: 15px;
        margin: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .team-member h4 {
        font-size: 22px;
        font-weight: bold;
        color: #81c784;
    }
    .team-member p {
        font-size: 18px;
        color: #cfd8dc;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div style="background-color: #212121; padding: 20px; border-radius: 15px; margin-bottom: 20px;">'
    '<h1 class="header">Handwritten Notes to Digital Notes</h1>'
    '<p style="text-align: center; font-size: 1.2rem; color: #b0bec5; max-width: 800px; margin: 0 auto;">'
    'This application leverages cutting-edge AI technology to convert your handwritten notes into well-structured digital formats. '
    'Choose between plain text, Markdown, for seamless integration into your projects or documents. '
    'Experience a sleek and intuitive design tailored for dark mode lovers.'
    '</p>'
    '</div>',
    unsafe_allow_html=True
)

# File upload and processing
left_column, right_column = st.columns(2)

with left_column:
    st.session_state.uploaded_file = st.file_uploader("Upload a PDF containing handwritten notes", type=["pdf"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.plain_text_convert = st.button("Convert to Plain Text")
    with col2:
        st.session_state.markdown_convert = st.button("Convert to Markdown")

    if st.session_state.uploaded_file:
        st.session_state.images = pdf_to_images(st.session_state.uploaded_file)
        st.write(f"Uploaded PDF contains {len(st.session_state.images)} pages.")

with right_column:
    if st.session_state.uploaded_file:
        pdf_viewer(input=st.session_state.uploaded_file.getvalue(), height=400)

# Processing file after upload
if (st.session_state.plain_text_convert or st.session_state.markdown_convert or st.session_state.latex_convert) and st.session_state.images:
    process_file()

# Display the converted content
st.subheader("Converted Content")
st.text_area("Output", value=st.session_state.output, height=300)

# Display character frequency
if st.session_state.output:
    st.subheader("Character Frequency Visualization")
    freq_data = generate_character_frequency(st.session_state.output)
    fig = px.bar(freq_data, x='Character', y='Frequency', title='Character Frequency', color='Frequency',
                 color_continuous_scale=px.colors.sequential.Viridis)
    st.plotly_chart(fig)

# Download the converted file
st.download_button(
    label="Download Converted File",
    data=st.session_state.output,
    file_name="converted_notes.txt" if st.session_state.format_selected == "Plain Text" else "converted_notes.md" if st.session_state.format_selected == "Markdown" else "converted_notes.tex",
    mime="text/plain" if st.session_state.format_selected == "Plain Text" else "text/markdown" if st.session_state.format_selected == "Markdown" else "application/x-tex"
)

# Team Members Section
st.markdown(
    """
    <div style="padding: 30px; margin-top: 30px; background-color: #263238; border-radius: 15px;">
        <h2 style="text-align: center; color: #4caf50; font-weight: bold;">Development with serivce</h2>
        <div style="display: flex; justify-content: center; flex-wrap: wrap;">
            <div class="team-member">
                <h4>Dhanush M (040)</h4>
                <ul><li>Lead Developer</li>
                <li> AI Specialist</li>
                <li>Front-End Developer</li>
                <li>Project Management</li></ul>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Footer Section
st.markdown(
    """
    <div class="footer">
        <p>© Handwritten Notes Digitalization App. All Rights Reserved 2025 Designed By : Dhanush M, M/2004/CSE/040 </p>
        <p>Hindusthan, Coimbatore, TamilNadu</p>
    </div>
    """,
    unsafe_allow_html=True
)
