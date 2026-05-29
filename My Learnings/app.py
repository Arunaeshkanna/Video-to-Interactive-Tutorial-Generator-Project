from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.agents import TutorialCrew
from src.config import AppConfig
from src.diagram import mermaid_block_to_html
from src.exporter import build_markdown, make_download_name
from src.features import FeatureLab, load_history, save_history, speech_html
from src.frames import extract_key_frames
from src.pdf_export import markdown_to_pdf_bytes
from src.transcript import get_transcript_from_upload, get_transcript_from_youtube
from src.youtube import download_youtube_video, is_youtube_url


load_dotenv()


def page_style() -> None:
    st.set_page_config(
        page_title="Video Tutorial Generator",
        page_icon="VT",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --ink: #12202f;
            --muted: #5a6878;
            --line: rgba(18, 32, 47, .12);
            --panel: rgba(255, 255, 255, .78);
            --accent: #0f8b8d;
            --accent-2: #e76f51;
            --gold: #f4a261;
        }
        .stApp {
            background:
                radial-gradient(circle at 8% 8%, rgba(15,139,141,.18), transparent 28rem),
                radial-gradient(circle at 92% 3%, rgba(231,111,81,.16), transparent 24rem),
                linear-gradient(135deg, #f8fbfc 0%, #eef6f3 48%, #fff7ef 100%);
            color: var(--ink);
        }
        [data-testid="stSidebar"] {
            background: rgba(255,255,255,.72);
            border-right: 1px solid var(--line);
        }
        .hero {
            padding: 1.35rem 1.45rem;
            border: 1px solid var(--line);
            background: linear-gradient(135deg, rgba(255,255,255,.9), rgba(255,255,255,.58));
            border-radius: 8px;
            box-shadow: 0 18px 48px rgba(18,32,47,.10);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(2rem, 4vw, 4.6rem);
            line-height: .98;
            letter-spacing: 0;
            color: #12202f;
        }
        .hero p {
            color: var(--muted);
            font-size: 1.02rem;
            max-width: 70rem;
            margin-top: .8rem;
        }
        .metric-card {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 8px;
            padding: .9rem 1rem;
            min-height: 6.4rem;
        }
        .metric-card .label {
            color: var(--muted);
            font-size: .82rem;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        .metric-card .value {
            color: var(--ink);
            font-size: 1.85rem;
            font-weight: 760;
            margin-top: .15rem;
        }
        .frame-img img {
            border-radius: 8px;
            border: 1px solid var(--line);
        }
        .small-muted {
            color: var(--muted);
            font-size: .9rem;
        }
        div.stButton > button, div.stDownloadButton > button {
            border-radius: 8px;
            border: 1px solid rgba(15,139,141,.28);
            background: #0f8b8d;
            color: white;
            font-weight: 700;
            min-height: 2.8rem;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover {
            border-color: #0b6d70;
            background: #0b7779;
            color: white;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: .7rem 1rem;
            background: rgba(255,255,255,.6);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(config: AppConfig) -> tuple[str, object, int, str, str, str]:
    st.sidebar.header("Source")
    source_mode = st.sidebar.radio("Input type", ["YouTube URL", "Upload video"], label_visibility="collapsed")

    youtube_url = ""
    uploaded_file = None
    if source_mode == "YouTube URL":
        youtube_url = st.sidebar.text_input("YouTube link", placeholder="https://www.youtube.com/watch?v=...")
    else:
        uploaded_file = st.sidebar.file_uploader("Upload video", type=["mp4", "mov", "mkv", "avi", "webm", "m4v"])

    st.sidebar.header("Generation")
    frame_count = st.sidebar.slider("Key frames", 3, min(16, config.max_key_frames), min(8, config.max_key_frames))
    tone = st.sidebar.selectbox("Tutorial style", ["Developer guide", "Beginner friendly", "Interview notes", "Workshop handout"])
    difficulty = st.sidebar.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced", "Interview prep", "Exam notes"])
    language = st.sidebar.selectbox("Language", ["English", "Tamil", "Hindi", "Spanish", "French", "German", "Japanese"])

    st.sidebar.caption("API keys and model settings are loaded only from `.env`.")
    return youtube_url, uploaded_file, frame_count, tone, difficulty, language


def process_video(config: AppConfig, youtube_url: str, uploaded_file, frame_count: int, tone: str, difficulty: str, language: str) -> dict:
    work_dir = config.storage_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    video_path: Path | None = None
    title = "Uploaded technical video"
    transcript = ""

    if youtube_url:
        if not is_youtube_url(youtube_url):
            raise ValueError("Please enter a valid YouTube URL.")
        transcript, title = get_transcript_from_youtube(youtube_url)
        if config.youtube_frame_download:
            try:
                video_path = download_youtube_video(youtube_url, work_dir)
            except Exception:
                video_path = None
    elif uploaded_file is not None:
        suffix = Path(uploaded_file.name).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=work_dir) as tmp:
            tmp.write(uploaded_file.getbuffer())
            video_path = Path(tmp.name)
        title = Path(uploaded_file.name).stem.replace("_", " ").replace("-", " ").title()
        transcript = get_transcript_from_upload(video_path, config)
    else:
        raise ValueError("Add a YouTube URL or upload a video first.")

    if not transcript.strip():
        raise ValueError("No transcript could be extracted. Try a video with captions or configure `GROQ_API_KEY` for transcription.")

    frames = []
    if video_path and video_path.exists():
        frames = extract_key_frames(video_path, work_dir / "frames", frame_count)

    crew = TutorialCrew(config)
    result = crew.run(title=title, transcript=transcript, frames=frames, tone=f"{tone} for {difficulty} learners")
    markdown = build_markdown(title, result, frames)

    data = {
        "title": title,
        "transcript": transcript,
        "frames": frames,
        "result": result,
        "markdown": markdown,
        "difficulty": difficulty,
        "language": language,
    }
    save_history(config.storage_dir, data)
    return data


def feature_key(name: str, data: dict, *parts: str) -> str:
    joined = "_".join([name, data["title"], data.get("difficulty", ""), data.get("language", ""), *parts])
    return str(abs(hash(joined)))


def render_list_section(title: str, items: list[str]) -> None:
    st.markdown(f"#### {title}")
    if not items:
        st.caption("Nothing strong was detected for this section.")
        return
    for item in items:
        st.markdown(f"- {item}")


def render_chat_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    history_key = feature_key("chat_messages", data)
    st.session_state.setdefault(history_key, [])

    for message in st.session_state[history_key]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask anything about this video")
    if question:
        st.session_state[history_key].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Searching the transcript and thinking..."):
                answer = lab.answer_question(data["transcript"], question)
            st.write(answer)
        st.session_state[history_key].append({"role": "assistant", "content": answer})


def render_quiz_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    key = feature_key("quiz", data)
    if st.button("Generate quiz", key=f"quiz_btn_{key}", width="stretch") or key in st.session_state:
        if key not in st.session_state:
            with st.spinner("Creating quiz questions..."):
                st.session_state[key] = lab.quiz(data["title"], data["transcript"], data["difficulty"])
        score = 0
        total = len(st.session_state[key])
        for index, item in enumerate(st.session_state[key], start=1):
            st.markdown(f"#### {index}. {item.get('question', 'Question')}")
            if item.get("type") == "mcq" and item.get("options"):
                answer = st.radio("Choose one", item["options"], key=f"quiz_{key}_{index}", label_visibility="collapsed")
            else:
                answer = st.text_input("Your answer", key=f"quiz_{key}_{index}")
            with st.expander("Show answer"):
                st.write(item.get("answer", ""))
                st.caption(item.get("explanation", ""))
                if answer and str(answer).strip().lower() in str(item.get("answer", "")).strip().lower():
                    score += 1
        st.info(f"Self-check score estimate: {score}/{total}")


def render_code_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    key = feature_key("code", data)
    if st.button("Extract code and commands", key=f"code_btn_{key}", width="stretch") or key in st.session_state:
        if key not in st.session_state:
            with st.spinner("Extracting commands, APIs, packages, and files..."):
                st.session_state[key] = lab.code_extract(data["title"], data["transcript"])
        extracted = st.session_state[key]
        render_list_section("Commands", extracted["commands"])
        render_list_section("APIs", extracted["apis"])
        render_list_section("Packages", extracted["packages"])
        render_list_section("Files", extracted["files"])
        render_list_section("Notes", extracted["notes"])


def render_flashcards_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    key = feature_key("flashcards", data)
    if st.button("Generate flashcards", key=f"flash_btn_{key}", width="stretch") or key in st.session_state:
        if key not in st.session_state:
            with st.spinner("Building flashcards..."):
                st.session_state[key] = lab.flashcards(data["title"], data["transcript"], data["difficulty"])
        cols = st.columns(2)
        for index, card in enumerate(st.session_state[key]):
            with cols[index % 2]:
                with st.expander(card.get("front", "Concept")):
                    st.write(card.get("back", ""))


def render_learning_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    key = feature_key("learning", data)
    if st.button("Generate learning path", key=f"learn_btn_{key}", width="stretch") or key in st.session_state:
        if key not in st.session_state:
            with st.spinner("Designing a learning path..."):
                st.session_state[key] = lab.learning_path(data["title"], data["transcript"], data["difficulty"])
        path = st.session_state[key]
        render_list_section("Learn Before This", path["before"])
        render_list_section("Learn After This", path["after"])
        render_list_section("Project Ideas", path["projects"])
        render_list_section("Resource Directions", path["resources"])


def render_summary_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    key = feature_key("summaries", data)
    if st.button("Generate summary variants", key=f"summary_btn_{key}", width="stretch") or key in st.session_state:
        if key not in st.session_state:
            with st.spinner("Creating summary formats..."):
                st.session_state[key] = lab.summaries(data["title"], data["transcript"])
        summaries = st.session_state[key]
        labels = {
            "thirty_second": "30-Second Summary",
            "five_minute": "5-Minute Notes",
            "linkedin_post": "LinkedIn Post",
            "youtube_description": "YouTube Description",
            "full_notes": "Full Notes",
        }
        for name, label in labels.items():
            with st.expander(label, expanded=name == "thirty_second"):
                st.markdown(summaries.get(name, ""))


def render_translate_tab(config: AppConfig, data: dict) -> None:
    lab = FeatureLab(config)
    col_a, col_b = st.columns(2)
    with col_a:
        target_language = st.selectbox("Target language", ["English", "Tamil", "Hindi", "Spanish", "French", "German", "Japanese"], index=0)
    with col_b:
        target_difficulty = st.selectbox("Target difficulty", ["Beginner", "Intermediate", "Advanced", "Interview prep", "Exam notes"], index=1)

    lang_key = feature_key("translate", data, target_language)
    diff_key = feature_key("difficulty", data, target_difficulty)

    if st.button("Translate tutorial", key=f"translate_btn_{lang_key}", width="stretch"):
        with st.spinner("Translating tutorial..."):
            st.session_state[lang_key] = lab.translate(data["title"], data["markdown"], target_language, target_difficulty)
    if lang_key in st.session_state:
        st.markdown(st.session_state[lang_key])
        st.download_button("Download translated markdown", st.session_state[lang_key], file_name=f"{target_language.lower()}-{make_download_name(data['title'])}", mime="text/markdown")

    if st.button("Rewrite for selected difficulty", key=f"diff_btn_{diff_key}", width="stretch"):
        with st.spinner("Adapting difficulty..."):
            st.session_state[diff_key] = lab.rewrite_for_difficulty(data["title"], data["markdown"], target_difficulty)
    if diff_key in st.session_state:
        st.markdown(st.session_state[diff_key])


def render_diagram_editor(data: dict) -> None:
    diagrams = data["result"].diagrams
    if not diagrams:
        st.warning("No diagrams available to edit.")
        return
    selected = st.selectbox("Diagram", list(range(1, len(diagrams) + 1)), format_func=lambda item: diagrams[item - 1].title)
    diagram = diagrams[selected - 1]
    edit_key = feature_key("diagram_edit", data, str(selected))
    code = st.text_area("Mermaid code", value=st.session_state.get(edit_key, diagram.code), height=220)
    st.session_state[edit_key] = code
    st.components.v1.html(mermaid_block_to_html(code), height=430, scrolling=True)


def render_voice_tab(data: dict) -> None:
    voice_source = st.selectbox("Voice source", ["30-second summary", "Tutorial intro", "Full tutorial"])
    if voice_source == "Full tutorial":
        text = data["markdown"]
    elif voice_source == "Tutorial intro":
        text = data["result"].summary
    else:
        text = data["result"].summary[:1200]
    st.components.v1.html(speech_html(text), height=360, scrolling=False)


def render_history_tab(config: AppConfig) -> None:
    items = load_history(config.storage_dir)
    if not items:
        st.info("No saved tutorials yet. Generate one and it will appear here.")
        return
    for item in items[:20]:
        with st.expander(f"{item.get('title', 'Untitled')} - {item.get('created_at', '')}"):
            st.caption(item.get("path", ""))
            st.download_button(
                "Download saved markdown",
                item.get("markdown", ""),
                file_name=make_download_name(item.get("title", "tutorial")),
                mime="text/markdown",
                key=f"history_{item.get('path')}",
            )


def main() -> None:
    page_style()
    config = AppConfig.from_env()

    st.markdown(
        """
        <section class="hero">
            <h1>Video-to-Interactive-Tutorial Generator</h1>
            <p>Convert technical videos into readable tutorials, key-frame notes, RAG-backed explanations, and clean Mermaid diagrams.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    youtube_url, uploaded_file, frame_count, tone, difficulty, language = render_sidebar(config)

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        metric_card("Pipeline", "12 features")
    with col_b:
        metric_card("Input", "URL / file")
    with col_c:
        metric_card("Output", "Blog + diagrams")
    with col_d:
        metric_card("Secrets", ".env only")

    st.write("")
    run_clicked = st.button("Generate tutorial", width="stretch")

    if run_clicked:
        with st.status("Watching, reading, and structuring the tutorial...", expanded=True) as status:
            try:
                st.write("Extracting transcript and key frames")
                data = process_video(config, youtube_url.strip(), uploaded_file, frame_count, tone, difficulty, language)
                st.write("Running RAG and tutorial agents")
                status.update(label="Tutorial generated", state="complete", expanded=False)
                st.session_state["tutorial_data"] = data
            except Exception as exc:
                status.update(label="Generation failed", state="error", expanded=True)
                st.error(str(exc))

    data = st.session_state.get("tutorial_data")
    if not data:
        st.info("Add a YouTube link or upload a video, then generate the tutorial.")
        st.markdown(
            """
            <div class="small-muted">
            The app supports captioned YouTube videos immediately. For uploaded videos, configure Groq in `.env` to enable transcription.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    result = data["result"]
    frames = data["frames"]

    st.subheader(data["title"])
    tabs = st.tabs(
        [
            "Tutorial",
            "Chat",
            "Quiz",
            "Code",
            "Flashcards",
            "Learning Path",
            "Summaries",
            "Translate",
            "Diagrams",
            "Diagram Editor",
            "Voice",
            "Key frames",
            "Transcript",
            "Export",
            "History",
        ]
    )

    with tabs[0]:
        st.markdown(result.blog)
        st.divider()
        st.markdown("#### Interactive checkpoints")
        for item in result.checkpoints:
            with st.expander(item["question"]):
                st.write(item["answer"])

    with tabs[1]:
        render_chat_tab(config, data)

    with tabs[2]:
        render_quiz_tab(config, data)

    with tabs[3]:
        render_code_tab(config, data)

    with tabs[4]:
        render_flashcards_tab(config, data)

    with tabs[5]:
        render_learning_tab(config, data)

    with tabs[6]:
        render_summary_tab(config, data)

    with tabs[7]:
        render_translate_tab(config, data)

    with tabs[8]:
        for index, diagram in enumerate(result.diagrams, start=1):
            st.markdown(f"#### Diagram {index}: {diagram.title}")
            st.components.v1.html(mermaid_block_to_html(diagram.code), height=420, scrolling=True)

    with tabs[9]:
        render_diagram_editor(data)

    with tabs[10]:
        render_voice_tab(data)

    with tabs[11]:
        if frames:
            cols = st.columns(2)
            for idx, frame in enumerate(frames):
                with cols[idx % 2]:
                    st.image(str(frame.path), caption=f"{frame.timestamp_label} - {frame.caption}", width="stretch")
        else:
            st.warning("No frames were extracted. This can happen when the video download is unavailable.")

    with tabs[12]:
        st.text_area("Transcript", data["transcript"], height=420)

    with tabs[13]:
        st.download_button(
            "Download tutorial markdown",
            data=data["markdown"],
            file_name=make_download_name(data["title"]),
            mime="text/markdown",
            width="stretch",
        )
        try:
            pdf_bytes = markdown_to_pdf_bytes(data["title"], data["markdown"])
            st.download_button(
                "Download tutorial PDF",
                data=pdf_bytes,
                file_name=make_download_name(data["title"]).replace(".md", ".pdf"),
                mime="application/pdf",
                width="stretch",
            )
        except RuntimeError as exc:
            st.warning(str(exc))
        st.code(data["markdown"], language="markdown")

    with tabs[14]:
        render_history_tab(config)


if __name__ == "__main__":
    main()
