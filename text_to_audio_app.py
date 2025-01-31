import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
import os
import pdfplumber
import io
import re

# App Information
APP_NAME = "PDF Speech Assistant"
AUTHOR = "Anthony Onoja"
EMAIL = "a.onoja@surrey.ac.uk"
INSTITUTION = "University of Surrey, UK"

# Constants
AVERAGE_WORDS_PER_MINUTE = 150  # Average reading speed in words per minute

# Initialize session state variables
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'next_clicked' not in st.session_state:
    st.session_state.next_clicked = False

@st.cache_data
def extract_main_text_from_pdf(uploaded_file):
    """Extracts main body text from a PDF, ignoring headers and footers."""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = [line for line in text.split("\n") if len(line) > 5]
                clean_text = " ".join(lines)
                clean_text = re.split(r"\bReferences\b", clean_text, flags=re.IGNORECASE)[0]
                pages.append(clean_text.strip())
        return pages
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return None

def generate_audio(text, accent, voice_gender):
    """Generates an audio file using Google TTS."""
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
    """Plays the audio for selected pages and enables auto-next functionality."""
    if start_page <= st.session_state.current_page < end_page:
        text = pages[st.session_state.current_page]
        with st.spinner(f"Generating audio for Page {st.session_state.current_page + 1}..."):
            audio_file = generate_audio(text, accent, voice_gender)

        if audio_file:
            st.audio(audio_file, format="audio/mp3")

            # JavaScript to auto-click the next button when audio ends
            autoplay_script = """
            <script>
                var audio = document.querySelector("audio");
                if (audio) {
                    audio.onended = function() {
                        var nextButton = window.parent.document.getElementById("next_page_button");
                        if (nextButton) { nextButton.click(); }
                    };
                }
            </script>
            """
            components.html(autoplay_script, height=0)

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
            st.success("Text extraction complete!")
            total_pages = len(pages)

            # Listening Time Selection
            st.subheader("Listening Time")
            listening_time = st.selectbox(
                "How long do you want to listen?",
                ["30 minutes", "1 hour", "2 hours", "More than 2 hours"],
                index=1
            )

            # Convert listening time to minutes
            listening_minutes = {"30 minutes": 0.5, "1 hour": 1, "2 hours": 2, "More than 2 hours": 3}[listening_time]
            pages_to_read = min(len(pages), int((AVERAGE_WORDS_PER_MINUTE * listening_minutes * 60) / 
                                                 (sum(len(page.split()) for page in pages) / len(pages))))

            # Page selection slider
            st.subheader("Select Pages to Listen To")
            start_page, end_page = st.slider(
                "Select page range:",
                min_value=1,
                max_value=total_pages,
                value=(1, pages_to_read),
                key="page_range"
            )

            start_page -= 1  # Convert to zero-based index
            end_page -= 1

            # Audio Settings
            st.subheader("Audio Settings")
            accent = st.selectbox("Select Accent:", ["British English", "American English", "Australian English"], index=0)
            voice_gender = st.selectbox("Select Voice Gender:", ["Male", "Female"], index=0)

            # Play/Stop buttons
            if st.session_state.is_playing:
                if st.button("Stop Audio", key="stop_audio"):
                    st.session_state.is_playing = False
                    st.session_state.current_page = start_page
                    st.session_state.next_clicked = False
            else:
                if st.button("Play Audio", key="play_audio"):
                    st.session_state.is_playing = True
                    st.session_state.current_page = start_page
                    st.session_state.next_clicked = False

            # Play audio and handle navigation
            if st.session_state.is_playing:
                play_audio(pages, start_page, end_page + 1, accent, voice_gender)

                # "Next Page" button (auto-clicked via JS)
                if st.button("Next Page", key="next_page_button"):
                    if st.session_state.current_page < end_page:
                        st.session_state.current_page += 1
                        st.session_state.next_clicked = True

if __name__ == "__main__":
    main()
