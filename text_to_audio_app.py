import streamlit as st
from gtts import gTTS
import io
from bs4 import BeautifulSoup
import requests

# Function to fetch papers from PubMed
def fetch_papers(query, max_results=10):
  url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax={max_results}&retmode=json"
  response = requests.get(url)
  id_list = response.json()['esearchresult']['idlist']

  papers = []
  for pubmed_id in id_list:
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pubmed_id}&retmode=xml"
    fetch_response = requests.get(fetch_url)
    soup = BeautifulSoup(fetch_response.content, 'xml')
    try:
      title = soup.find('ArticleTitle').text
      abstract = soup.find('AbstractText').text if soup.find('AbstractText') else 'No abstract available'
      pubmed_central_id = soup.find('PubmedCentralId')  # Look for PubMed Central ID
      pmcid = pubmed_central_id.text if pubmed_central_id else None  # Extract PMCID if available

      # Build link to full text (use PMCID if available, otherwise use PubMed link)
      if pmcid:
        full_text_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}"
      else:
        full_text_link = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"

      sections = {
          'Title': title,
          'Abstract': abstract,
          'Full Text Link': full_text_link,
      }
      papers.append(sections)
    except AttributeError:
      continue
  return papers

# Streamlit app interface
st.title("PaperVox - ")
st.subheader("An AI-Powered Research Paper Audio Summaries App")
st.subheader("Onoja Anthony")

st.write("About: Tired of reading research papers? This app helps you explore scientific literature through audio. \n Simply enter your search query, and PaperVox will find relevant papers from PubMed. ")
# Input for search query
query = st.text_input("Enter your search query", "AI Machine Learning Biomedical Health Sciences")

# Session state to store papers
if 'papers' not in st.session_state:
  st.session_state.papers = []

# Button to search
if st.button("Search"):
  # Fetch papers
  st.session_state.papers = fetch_papers(query)
  st.session_state.search_done = True

# Display papers if search is done
if st.session_state.get('search_done', False):
  # Filter papers
  keywords = ["AI", "Machine Learning", "Biomedical", "Health Sciences"]
  top_papers = st.session_state.papers[:5]

  # Display top 5 papers
  for i, paper in enumerate(top_papers):
    st.write(f"**{i+1}. {paper['Title']}**")
    st.write(f"*Abstract:* {paper['Abstract']}")
    # Button to generate audio for the abstract
    if st.button(f"Listen to Abstract {i+1}"):
      text = paper['Abstract']
      try:
        # Generate audio using gTTS
        tts = gTTS(text=text, lang='en')
        audio_file = io.BytesIO()
        tts.write_to_fp(audio_file)
        audio_file.seek(0)
        st.audio(audio_file, format='audio/mp3')
      except Exception as e:
        st.error(f"Error generating audio: {e}")
    st.write(f"*Full Text:* [Link]({paper['Full Text Link']})")
    st.write("")
