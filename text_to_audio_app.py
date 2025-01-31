import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
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

# Constants
AVERAGE_WORDS_PER_MINUTE = 150  # Average reading speed in words per minute

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
    """Plays the audio for selected pages with auto-next feature."""
    while st.session_state.current_page < end_page:
        if not st.session_state.is_playing:
            break

        text = pages[st.session_state.current_page]
        with st.spinner(f"Generating audio for Page {st.session_state.current_page + 1}..."):
            audio_file = generate_audio(text, accent, voice_gender)

        if audio_file:
            st.audio(audio_file, format="audio/mp3")

            # JavaScript to auto-click a hidden button after audio ends
            autoplay_script = """
            <script>
                var audio = document.querySelector("audio");
                if (audio) {
                    audio.onended = function() {
                        var nextButton = document.getElementById("next_page_button");
                        if (nextButton) { nextButton.click(); }
                    };
                }
            </script>
            """
            components.html(autoplay_script, height=0)

            # Hidden button to trigger next page
            if st.button("Next Page", key=f"next_{st.session_state.current_page}"):
                st.session_state.current_page += 1
                st.experimental_rerun()

            time.sleep(1)  # Short delay before moving to next page

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
            listening_minutes = {"30 minutes": 0.5, "1 hour": 1, "2 hours": 2, "More than 2 hours": 3}[listening_time]

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
                    st.experimental_rerun()  # Refresh the app to stop audio playback
            else:
                play_button = st.button("Play Audio")
                if play_button:
                    st.session_state.is_playing = True
                    st.session_state.current_page = start_page  # Start from the selected page
                    play_audio(pages, start_page, end_page + 1, accent, voice_gender)  # Play audio for the selected range

if __name__ == "__main__":
    main()
