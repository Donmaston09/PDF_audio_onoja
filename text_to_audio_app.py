import streamlit as st
from gtts import gTTS
import os
import pdfplumber
import io
import time
import re
import base64

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
if 'audio_files' not in st.session_state:
    st.session_state.audio_files = []

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

                # Exclude "References" section if found
                clean_text = re.split(r"\bReferences\b", clean_text, flags=re.IGNORECASE)[0]

                pages.append(clean_text.strip())

        return pages
    except Exception as e:
        st.error(f"Error extracting text: {e}")
        return None

def generate_audio(text, accent, voice_gender):
    """Generates and returns an audio file using Google TTS (gTTS) with selected accent and voice gender."""
    try:
        # Map accents to gTTS language codes
        accent_map = {
            "British English": "en-UK",
            "American English": "en-US",
            "Australian English": "en-AU"
        }

        # Map voice gender to gTTS top-level domains (tld)
        # Note: gTTS does not directly support male/female voices, but tld can influence voice characteristics
        voice_gender_map = {
            "Male": "co.uk",  # British English domain (often male voice)
            "Female": "com.au"  # Australian English domain (often female voice)
        }

        # Convert text to speech using gTTS
        tts = gTTS(
            text=text,
            lang=accent_map[accent],
            tld=voice_gender_map[voice_gender]
        )

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

def play_audio(pages, start_page, end_page, accent, voice_gender):
    """Function to generate audio files for selected pages and store them in session state."""
    st.session_state.audio_files = []
    for i in range(start_page, end_page):
        text = pages[i]
        audio_file = generate_audio(text, accent, voice_gender)
        if audio_file:
            st.session_state.audio_files.append(audio_file)

def autoplay_audio(audio_files):
    """Function to auto-play audio files sequentially using JavaScript."""
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
    st.markdown(js_code, unsafe_allow_html=True)

def calculate_page_range(pages, listening_time):
    """Calculates the number of pages that can be read within the selected listening time."""
    total_words = sum(len(page.split()) for page in pages)
    total_minutes = listening_time * 60  # Convert hours to minutes
    words_per_page = total_words / len(pages)

    # Calculate the number of pages that can be read in the selected time
    pages_to_read = int((AVERAGE_WORDS_PER_MINUTE * total_minutes) / words_per_page)
    return min(pages_to_read, len(pages))  # Ensure it doesn't exceed total pages

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

            # Display listening time selection
            st.subheader("Listening Time")
            listening_time = st.selectbox(
                "How long do you want to listen?",
                ["30 minutes", "1 hour", "2 hours", "More than 2 hours"],
                index=1
            )

            # Convert listening time to minutes
            if listening_time == "30 minutes":
                listening_minutes = 0.5
            elif listening_time == "1 hour":
                listening_minutes = 1
            elif listening_time == "2 hours":
                listening_minutes = 2
            else:
                listening_minutes = 3  # Default for "More than 2 hours"

            # Calculate the number of pages to read based on listening time
            pages_to_read = calculate_page_range(pages, listening_minutes)

            # Display page selection slider
            st.subheader("Select Pages to Listen To")
            start_page, end_page = st.slider(
                "Select page range:",
                min_value=1,
                max_value=total_pages,
                value=(1, pages_to_read),  # Default to calculated pages
                key="page_range"
            )

            # Adjust to zero-based indexing
            start_page -= 1
            end_page -= 1

            # Display accent and voice gender options
            st.subheader("Audio Settings")
            accent = st.selectbox(
                "Select Accent:",
                ["British English", "American English", "Australian English"],
                index=0
            )
            voice_gender = st.selectbox(
                "Select Voice Gender:",
                ["Male", "Female"],
                index=0
            )

            # Play/Stop buttons
            if st.session_state.is_playing:
                stop_button = st.button("Stop Audio")
                if stop_button:
                    st.session_state.is_playing = False
                    st.session_state.current_page = start_page  # Reset to the start of the selected range
                    st.session_state.audio_files = []  # Clear audio files
                    st.experimental_rerun()  # Refresh the app to stop audio playback
            else:
                play_button = st.button("Play Audio")
                if play_button:
                    st.session_state.is_playing = True
                    play_audio(pages, start_page, end_page + 1, accent, voice_gender)  # Generate audio files
                    autoplay_audio(st.session_state.audio_files)  # Auto-play audio files sequentially

if __name__ == "__main__":
    main()
