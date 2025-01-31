import streamlit as st
import streamlit.components.v1 as components
import qrcode
from gtts import gTTS
import os
import pdfplumber
import io
import re
import time
import base64
import requests
from bs4 import BeautifulSoup

# App Information
APP_NAME = "PDF and Web Speech Assistant"
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
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []

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

# Function to extract text from a web page
def extract_text_from_url(url):
    try:
        # Simulate a browser request by adding headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Fetch the web page content with headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract the main content (e.g., article body)
        main_content = soup.find("article") or soup.find("main") or soup.find("body")
        if main_content:
            # Remove script and style tags
            for tag in main_content(["script", "style"]):
                tag.decompose()

            # Get the text and clean it up
            text = main_content.get_text(separator="\n")
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            clean_text = "\n".join(lines)
            return clean_text
        else:
            st.error("Could not extract main content from the web page.")
            return None
    except Exception as e:
        st.error(f"Error extracting text from URL: {e}")
        return None

# Function to extract text from a PDF
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

# Function to generate audio from text
def generate_audio(text, accent, voice_gender):
    try:
        # Map accents and voice genders to gTTS parameters
        accent_map = {"British English": "en-UK", "American English": "en-US", "Australian English": "en-AU"}
        voice_gender_map = {"Male": "co.uk", "Female": "com.au"}

        # Convert text to speech using gTTS
        tts = gTTS(text=text, lang=accent_map[accent], tld=voice_gender_map[voice_gender])

        # Save to temporary file
        audio_file_path = "temp_audio.mp3"
        tts.save(audio_file_path)

        # Load the audio file into a BytesIO stream
        audio_file = io.BytesIO()
        with open(audio_file_path, 'rb') as f:
            audio_file.write(f.read())

        os.remove(audio_file_path)  # Clean up temporary file
        audio_file.seek(0)  # Reset file pointer

        return audio_file
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

# Function to play audio files sequentially
def autoplay_audio(audio_files):
    if not audio_files:
        return

    # Create a list of base64-encoded audio files
    audio_base64_list = [base64.b64encode(audio_file.getvalue()).decode("utf-8") for audio_file in audio_files]

    # Generate JavaScript code to play audio files sequentially
    js_code = f"""
        <audio id="audioPlayer" controls autoplay>
            <source src="data:audio/mp3;base64,{audio_base64_list[0]}" type="audio/mp3">
        </audio>
        <script>
            let audioFiles = {audio_base64_list};
            let currentIndex = 0;
            const audioPlayer = document.getElementById("audioPlayer");

            audioPlayer.addEventListener("ended", function() {{
                currentIndex++;
                if (currentIndex < audioFiles.length) {{
                    audioPlayer.src = "data:audio/mp3;base64," + audioFiles[currentIndex];
                    audioPlayer.play();
                }} else {{
                    audioPlayer.remove(); // Remove the audio player when done
                }}
            }});
        </script>
    """
    components.html(js_code, height=100)

# Main function to run the Streamlit app
def main():
    st.title(APP_NAME)
    st.write(f"Developed by {AUTHOR}, {INSTITUTION}")
    st.write(f"Contact: {EMAIL}")
    display_qr_code()

    # Option to upload PDF or paste URL
    input_option = st.radio("Choose input type:", ("Upload PDF", "Paste URL"))

    if input_option == "Upload PDF":
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
                        play_audio(pages, start_page, end_page, accent, voice_gender)
                        autoplay_audio(st.session_state.audio_files)
            else:
                st.error("No text was extracted from the PDF. Please try another file.")

    elif input_option == "Paste URL":
        url = st.text_input("Paste the URL of the web page:")
        if url:
            with st.spinner("Extracting main content from the web page..."):
                text = extract_text_from_url(url)
            if text:
                st.success("Text extraction complete!")
                pages = text.split("\n\n")  # Split text into "pages" based on paragraphs
                total_pages = len(pages)
                if total_pages > 0:
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
                            play_audio(pages, start_page, end_page, accent, voice_gender)
                            autoplay_audio(st.session_state.audio_files)
                else:
                    st.error("No text was extracted from the web page. Please try another URL.")
            else:
                st.error("Failed to extract text from the URL. Please check the URL and try again.")

# Run the app
if __name__ == "__main__":
    main()
