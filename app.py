import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarize import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

# ----------------------------------------------------------------------------
# Page config & styling
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
        .hero {
            padding: 1.6rem 1.8rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);
            color: white;
            margin-bottom: 1.2rem;
        }
        .hero h1 {margin: 0; font-size: 2rem; color: white;}
        .hero p {margin: .3rem 0 0 0; opacity: .9;}
        .title-card {
            padding: 1rem 1.3rem;
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,.25);
            background: rgba(128,128,128,.06);
            margin-bottom: 1rem;
        }
        .title-card h2 {margin: 0; font-size: 1.5rem;}
        .title-card span {opacity: .65; font-size: .85rem; text-transform: uppercase; letter-spacing: .06em;}
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.25);
            border-radius: 12px;
            padding: .7rem 1rem;
            background: rgba(128,128,128,.05);
        }
        .stTabs [data-baseweb="tab-list"] {gap: .4rem;}
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding: .5rem 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "result" not in st.session_state:
    st.session_state.result = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def reset_session():
    st.session_state.result = None
    st.session_state.messages = []


# ----------------------------------------------------------------------------
# Pipeline (same steps as the CLI, with progress reporting)
# ----------------------------------------------------------------------------
def run_pipeline_ui(source: str, language: str) -> dict:
    with st.status("Processing your video…", expanded=True) as status:
        st.write("🎧 Downloading / preparing audio…")
        chunks = process_input(source)

        st.write(f"📝 Transcribing {len(chunks)} audio chunk(s)…")
        transcript = transcribe_all(chunks, language)

        st.write("🏷️ Generating title…")
        title = generate_title(transcript)

        st.write("📋 Summarizing…")
        summary = summarize(transcript)

        st.write("✅ Extracting action items, decisions & questions…")
        action_items = extract_action_items(transcript)
        decisions = extract_key_decisions(transcript)
        questions = extract_questions(transcript)

        st.write("🧠 Building chat index (RAG)…")
        rag_chain = build_rag_chain(transcript)

        status.update(label="Done! 🎉", state="complete", expanded=False)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


def build_report(r: dict) -> str:
    return (
        f"# {r['title']}\n\n"
        f"## Summary\n{r['summary']}\n\n"
        f"## Action Items\n{r['action_items']}\n\n"
        f"## Key Decisions\n{r['key_decisions']}\n\n"
        f"## Open Questions\n{r['open_questions']}\n\n"
        f"## Full Transcript\n{r['transcript']}\n"
    )


# ----------------------------------------------------------------------------
# Sidebar — inputs
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Input")

    input_mode = st.radio(
        "Source type",
        ["YouTube URL", "Upload file"],
        horizontal=True,
    )

    youtube_url = ""
    uploaded = None
    if input_mode == "YouTube URL":
        youtube_url = st.text_input(
            "YouTube URL", placeholder="https://www.youtube.com/watch?v=..."
        )
    else:
        uploaded = st.file_uploader(
            "Audio / video file",
            type=["mp3", "wav", "m4a", "mp4", "mkv", "mov", "webm", "ogg", "flac"],
        )

    language = st.selectbox("Language", ["english", "hinglish"], index=0)

    run_clicked = st.button("🚀 Analyze", type="primary", use_container_width=True)

    if st.session_state.result is not None:
        st.button(
            "🗑️ Clear & start over",
            on_click=reset_session,
            use_container_width=True,
        )

    st.divider()
    st.caption("Transcribe → summarize → extract insights → chat with your video.")

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🎬 AI Video Assistant</h1>
        <p>Turn any video or meeting recording into a summary, action items, and a chat you can ask questions to.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
if run_clicked:
    source = None
    tmp_path = None

    if input_mode == "YouTube URL":
        if not youtube_url.strip():
            st.warning("Please enter a YouTube URL.")
        else:
            source = youtube_url.strip()
    else:
        if uploaded is None:
            st.warning("Please upload a file.")
        else:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            source = tmp_path

    if source:
        reset_session()
        try:
            st.session_state.result = run_pipeline_ui(source, language)
        except Exception as e:
            st.error(f"Something went wrong: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
result = st.session_state.result

if result is None:
    st.info("👈 Add a YouTube link or upload a file in the sidebar, then click **Analyze**.")
else:
    st.markdown(
        f"""
        <div class="title-card">
            <span>Title</span>
            <h2>{result['title']}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    words = len(result["transcript"].split())
    c1, c2, c3 = st.columns(3)
    c1.metric("Transcript words", f"{words:,}")
    c2.metric("Est. read time", f"{max(1, words // 200)} min")
    c3.metric("Language", language.capitalize())

    st.download_button(
        "⬇️ Download full report (.md)",
        data=build_report(result),
        file_name="video_report.md",
        mime="text/markdown",
    )

    tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
        [
            "📋 Summary",
            "✅ Action Items",
            "🔑 Key Decisions",
            "❓ Open Questions",
            "📄 Transcript",
            "💬 Chat",
        ]
    )

    with tab_summary:
        st.markdown(result["summary"])

    with tab_actions:
        st.markdown(result["action_items"])

    with tab_decisions:
        st.markdown(result["key_decisions"])

    with tab_questions:
        st.markdown(result["open_questions"])

    with tab_transcript:
        st.text_area(
            "Full transcript",
            value=result["transcript"],
            height=450,
            label_visibility="collapsed",
        )
        st.download_button(
            "⬇️ Download transcript (.txt)",
            data=result["transcript"],
            file_name="transcript.txt",
            mime="text/plain",
        )

    with tab_chat:
        st.caption("Ask anything about the video — answers come from the transcript.")

        if not st.session_state.messages:
            with st.chat_message("assistant"):
                st.markdown("Hi! Ask me anything about this video. 👋")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        question = st.chat_input("Ask a question about the video…")
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        answer = ask_question(result["rag_chain"], question)
                    except Exception as e:
                        answer = f"⚠️ Error: {e}"
                st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

        if st.session_state.messages:
            if st.button("Clear chat"):
                st.session_state.messages = []
                st.rerun()