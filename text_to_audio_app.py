import streamlit as st
import streamlit.components.v1 as components
import qrcode
from gtts import gTTS
import os
import pdfplumber
import io
import re
import time

# App Information
APP_NAME = "PDF Speech Assistant"
AUTHOR = "Anthony Onoja"
EMAIL = "a.onoja@surrey.ac.uk"
INSTITUTION = "University of Surrey, UK"

# Streamlit App Deployment URL (Replace with your actual Streamlit Cloud link)
APP_URL = "https://pdfaudioonoja-gpd5kkrbgzfwewkvtwmcvb.streamlit.app/"

# Constants
AVERAGE_WORDS_PER_MINUTE = 150

# Initialize session state variables
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# Function to generate QR Code
def generate_qr_code(link):
    qr = qrcode.make(link)
    qr_bytes = io.BytesIO()
    qr.save(qr_bytes, format="PNG")
    return qr_bytes.getvalue()

# Display QR Code in Sidebar
def display_qr_code():
    st.sidebar.subheader("Share this App")
    qr_image = generate_qr_code(APP_URL)
    st.sidebar.image(qr_image, caption="Scan to open the app", use_container_width=True)

@st.cache_data
def extract_main_text_from_pdf(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = text.split("\n")
                lines = [line for line in lines if len(line) > 5]
                clean_text = " ".join(lines)
                clean_text = re.split(r"\bReferences\b", clean_text, flags=re.IGNORECASE)[0]
                pages.append(clean_text.strip())
        return pages
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return None

def generate_audio(text, accent, voice_gender):
    try:
        accent_map = {"British English": "en-UK", "American English": "en-US", "Australian English": "en-AU"}
        voice_gender_map = {"Male": "co.uk", "Female": "com.au"}
        tts = gTTS(text=text, lang=accent_map[accent], tld=voice_gender_map[voice_gender])
        audio_file_path = "temp_audio.mp3"
        tts.save(audio_file_path)
        audio_file = io.BytesIO()
        with open(audio_file_path, 'rb') as f:
            audio_file.write(f.read())
        os.remove(audio_file_path)
        audio_file.seek(0)
        return audio_file
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

def play_audio(pages, start_page, end_page, accent, voice_gender):
    while st.session_state.current_page < end_page:
        if not st.session_state.is_playing:
            break
        text = pages[st.session_state.current_page]
        with st.spinner(f"Generating audio for Page {st.session_state.current_page + 1}..."):
            audio_file = generate_audio(text, accent, voice_gender)
        if audio_file:
            st.audio(audio_file, format="audio/mp3")
            st.session_state.current_page += 1
            time.sleep(1)

def main():
    st.title(APP_NAME)
    st.write(f"Developed by {AUTHOR}, {INSTITUTION}")
    st.write(f"Contact: {EMAIL}")
    display_qr_code()
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    if uploaded_file is not None:
        with st.spinner("Extracting main content from PDF..."):
            pages = extract_main_text_from_pdf(uploaded_file)
        if pages:
            st.success("Text extraction complete!")
            total_pages = len(pages)
            listening_time = st.selectbox("How long do you want to listen?", ["30 minutes", "1 hour", "2 hours", "More than 2 hours"], index=1)
            listening_minutes = {"30 minutes": 0.5, "1 hour": 1, "2 hours": 2, "More than 2 hours": 3}[listening_time]
            start_page, end_page = st.slider("Select page range:", min_value=1, max_value=total_pages, value=(1, total_pages))
            start_page -= 1
            end_page -= 1
            accent = st.selectbox("Select Accent:", ["British English", "American English", "Australian English"], index=0)
            voice_gender = st.selectbox("Select Voice Gender:", ["Male", "Female"], index=0)
            if st.session_state.is_playing:
                if st.button("Stop Audio"):
                    st.session_state.is_playing = False
                    st.session_state.current_page = start_page
                    st.experimental_rerun()
            else:
                if st.button("Play Audio"):
                    st.session_state.is_playing = True
                    st.session_state.current_page = start_page
                    play_audio(pages, start_page, end_page + 1, accent, voice_gender)

if __name__ == "__main__":
    main()
