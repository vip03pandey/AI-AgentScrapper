import streamlit as st
import requests
from typing import Literal

SOURCE_TYPES = Literal["both", "news", "reddit"]
BACKEND_URL = "http://localhost:8000"
def main():
    if 'topics' not in st.session_state:
        st.session_state.topics = []
    if 'input_key' not in st.session_state:
        st.session_state.input_key = 0

    st.title("AI Journalist")

    with st.sidebar:
        st.header("Settings")
        source_type: SOURCE_TYPES  = st.selectbox(
            "Data Sources",
            options=["both", "news", "reddit"],
            format_func=lambda x: "News 📰" if x == "news" else "Reddit 👽" if x == "reddit" else "Both"
        )

    st.markdown('#### Topic Management')
    col1, col2 = st.columns([4, 1])
    with col1:
        new_topic = st.text_input(
            "Enter a topic to analyze",
            key=f"topic_input_{st.session_state.input_key}",
            placeholder="e.g. Artificial Intelligence"
        )

    with col2:
        add_disabled = len(st.session_state.topics) >= 1 or not new_topic.strip()
        if st.button("Add", disabled=add_disabled):
            st.session_state.topics.append(new_topic.strip())
            st.session_state.input_key += 1 
            st.rerun()

    if st.session_state.topics:
        st.subheader(f"Selected Topics: {', '.join(st.session_state.topics)}")
        for i,topic in enumerate(st.session_state.topics):
            cols=st.columns([4, 1])
            cols[0].write(f"### {i+1}. {topic}")
            if cols[1].button("Remove",key=f"remove_{i}"):
                st.session_state.topics.remove(topic)
                st.rerun()

    st.markdown('---')
    st.subheader("Audio Generation")

    if st.button("Generate Summary", disabled=len(st.session_state.topics) == 0):
        if not st.session_state.topics:
            st.error("Please add at least one topic")
        else:
            with st.spinner("Analyzing the topics and generating the summary"):
                try:
                    response=requests.post(
                        f"{BACKEND_URL}/generate-news-summary",
                        json={
                            "topics":st.session_state.topics,
                            "source_type":source_type
                        }
                    )

                    if response.status_code == 200:
                        st.audio(response.content, format="audio/mpeg")
                        st.download_button(
                            data=response.content,
                            file_name="summary.mp3",
                            mime="audio/mpeg",
                            type="primary"
                        )
                        st.success("Audio summary generated successfully!")
                    else:
                        handle_api_error(response)
                except requests.exceptions.ConnectionError:
                    st.error("Failed to connect to the server. Please try again later.")
                except Exception as e:
                    st.error(e)

def handle_api_error(response):
    "Handle API errors"
    try:
        error_details=response.json().get("detail","Unknown error")
        st.error(f"API Error: ({response.status_code}) {error_details}")
    except:
        st.error(f"API Error: ({response.status_code}) {response.text}")
if __name__ == "__main__":
    main()
