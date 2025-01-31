import streamlit as st
import pyttsx3
import os
import pdfplumber
import io
import time
import re

# App Information
APP_NAME = "PDF Speech Assistant"
AUTHOR = "Anthony Onoja"
EMAIL = "a.onoja@surrey.ac.uk"
INSTITUTION = "University of Surrey, UK"

# Initialize session state variables
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

@st.cache_data
def extract_main_text_from_pdf(uploaded_file):
    """Extracts main body text from a PDF, ignoring author names, footers, and headers."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                
                # Remove header/footer (if any)
                lines = text.split("\n")
                lines = [line for line in lines if len(line) > 5]  # Ignore very short lines

                # Combine cleaned lines
                clean_text = " ".join(lines)

                # **Extract only main sections**
                if "abstract" in clean_text.lower():
                    abstract_start = clean_text.lower().index("abstract")
                    clean_text = clean_text[abstract_start:]  # Start from abstract
                    
                # Exclude "References" section if found
                clean_text = re.split(r"\bReferences\b", clean_text, flags=re.IGNORECASE)[0]

                pages.append(clean_text.strip())

        return pages
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return None

def generate_audio(text):
    """Generates and returns an audio file from text using pyttsx3 (offline TTS)."""
    try:
        engine = pyttsx3.init()
        
        # Save the speech to a temporary file
        audio_file_path = 'temp_audio.mp3'
        engine.save_to_file(text, audio_file_path)
        engine.runAndWait()

        # Read the audio file into a BytesIO stream
        audio_file = io.BytesIO()
        with open(audio_file_path, 'rb') as f:
            audio_file.write(f.read())

        os.remove(audio_file_path)  # Clean up temporary file
        audio_file.seek(0)  # Reset file pointer

        return audio_file
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

def play_audio(pages):
    """Function to play the audio page by page."""
    while st.session_state.current_page < len(pages):
        if not st.session_state.is_playing:
            break

        text = pages[st.session_state.current_page]
        audio_file = generate_audio(text)

        if audio_file:
            st.audio(audio_file, format="audio/mp3")
            st.session_state.current_page += 1
            time.sleep(1)  # Add delay for sequential audio processing

def main():
    """Main function to run the Streamlit app."""
    st.title(APP_NAME)
    st.write(f"Developed by {AUTHOR}, {INSTITUTION}")
    st.write(f"Contact: {EMAIL}")

    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if uploaded_file is not None:
        with st.spinner("Extracting main content from PDF..."):
            pages = extract_main_text_from_pdf(uploaded_file)

        if pages:
            # Display extracted text
            for i, text in enumerate(pages):
                st.subheader(f"Page {i + 1}")
                st.text_area(f"Extracted Main Text from Page {i + 1}:", text, height=150)

            # Play/Stop buttons
            if st.session_state.is_playing:
                stop_button = st.button("Stop Audio")
                if stop_button:
                    st.session_state.is_playing = False
                    st.session_state.current_page = 0  # Reset the page counter
            else:
                play_button = st.button("Play Audio")
                if play_button:
                    st.session_state.is_playing = True
                    play_audio(pages)  # Start playing audio sequentially

if __name__ == "__main__":
    main()
