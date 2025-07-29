import streamlit as st
import requests
import json
import traceback
import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import GenerationRecord

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Code Generator", layout="wide")

# Setup session states
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = True
if "generation_id" not in st.session_state:
    st.session_state.generation_id = None
if "results" not in st.session_state:
    st.session_state.results = {
        "ui_code": "",
        "db_schema": "",
        "backend_code": "",
        "db_queries": "",
        "tech_docs": "",
    }
if "progress" not in st.session_state:
    st.session_state.progress = {}
if "completed" not in st.session_state:
    st.session_state.completed = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar rendering
if st.session_state.sidebar_open:
    with st.sidebar:
        st.title("CodeGen")
        st.divider()
        if st.button("New Chat", use_container_width=True):
            st.session_state.generation_id = None
            st.session_state.results = {
                "ui_code": "",
                "db_schema": "",
                "backend_code": "",
                "db_queries": "",
                "tech_docs": "",
            }
            st.session_state.progress = {}
            st.session_state.completed = False
            st.session_state.messages = []
            st.rerun()
        st.divider()
        st.markdown("**Chats**")

        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def fetch_previous_chats():
            try:
                db = next(get_db())
                chats = (
                    db.query(GenerationRecord)
                    .order_by(GenerationRecord.created_at.desc())
                    .all()
                )
                return [
                    {
                        "id": chat.id,
                        "prompt": chat.prompt or "Image-based request",
                        "created_at": chat.created_at,
                    }
                    for chat in chats
                ]
            except Exception as e:
                st.error(f"Failed to fetch previous chats: {str(e)}")
                return []

        previous_chats = fetch_previous_chats()
        selected_chat = None
        if previous_chats:
            for chat in previous_chats:
                if st.button(
                    f"{chat['prompt'][:50]}... ({chat['created_at'].strftime('%Y-%m-%d %H:%M')})",
                    key=f"chat_{chat['id']}",
                ):
                    selected_chat = chat["id"]
        else:
            st.info("No previous chats found.")

        st.divider()
        st.subheader("Configuration")
        backend_lang = st.selectbox(
            "Backend Language", ["python", "javascript", "java", "go"], index=0
        )

        # Conditional framework rendering
        framework_options = {
            "python": ["none", "django", "flask", "fastApi"],
            "javascript": ["none", "express"],
            "java": ["none", "spring"],
            "go": ["none", "gin"],
        }
        framework = st.selectbox(
            "Framework", framework_options.get(backend_lang, ["none"]), index=0
        )

# Header
st.header("Ask your questions!")

# Main content container
main_container = st.container()

# Display chat history
with main_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["type"] == "text":
                st.write(message["content"])
            elif message["type"] == "image":
                st.image(
                    message["content"],
                    caption="Uploaded Wireframe",
                    use_column_width=True,
                )

# Container for chat results
results_container = st.container()


# Display loaded chat results
def display_chat_results():
    with results_container:
        results_container.empty()  # Clear previous results
        if st.session_state.results["ui_code"]:
            st.subheader("UI Code")
            st.code(st.session_state.results["ui_code"], language="html")
        if st.session_state.results["db_schema"]:
            st.subheader("Database Schema")
            st.code(st.session_state.results["db_schema"], language="sql")
        if st.session_state.results["backend_code"]:
            st.subheader(f"{backend_lang.capitalize()} Backend Code")
            st.code(st.session_state.results["backend_code"], language=backend_lang)
        if st.session_state.results["db_queries"]:
            st.subheader("Database Queries")
            st.code(st.session_state.results["db_queries"], language="sql")
        if st.session_state.results["tech_docs"]:
            st.subheader("Technical Documentation")
            st.markdown(st.session_state.results["tech_docs"])


# Chat input
with st.container():
    col_input, col_upload = st.columns([0.85, 0.15])
    with col_input:
        user_input = st.chat_input(
            "What can I help with? Ask anything...", key="chat_input"
        )
    with col_upload:
        # SVG icon for file uploader
        uploaded_file = st.file_uploader(
            "",
            type=["jpg", "png", "jpeg"],
            key="file_uploader",
            label_visibility="collapsed",
        )


def update_progress(step, status):
    st.session_state.progress[step] = status
    if status == "completed":
        st.toast("Code generation completed!", icon="✅")


def determine_generation_types(prompt: str):
    prompt = prompt.lower()
    types = {
        "ui_code": False,
        "db_schema": False,
        "backend_code": False,
        "db_queries": False,
        "tech_docs": False,
    }
    if re.search(r"\b(ui|frontend|html|css|javascript|react|interface)\b", prompt):
        types["ui_code"] = True
    if re.search(r"\b(database|schema|tables|sql schema|db design)\b", prompt):
        types["db_schema"] = True
    if re.search(
        r"\b(backend|api|server|python|javascript|java|go|django|flask|fastapi|express|spring|gin)\b",
        prompt,
    ):
        types["backend_code"] = True
    if re.search(
        r"\b(queries|sql|database queries|crud|select|insert|update|delete)\b", prompt
    ):
        types["db_queries"] = True
    if re.search(r"\b(documentation|docs|technical docs|readme|guide)\b", prompt):
        types["tech_docs"] = True
    if not any(types.values()) and prompt.strip():
        types = {key: True for key in types}
    return types


# Request Handling
if user_input or uploaded_file or selected_chat:
    if selected_chat:
        try:
            db = next(get_db())
            record = (
                db.query(GenerationRecord)
                .filter(GenerationRecord.id == selected_chat)
                .first()
            )
            if record:
                # Clear previous content
                st.session_state.messages = []
                st.session_state.results = {
                    "ui_code": record.ui_code or "",
                    "db_schema": record.db_schema or "",
                    "backend_code": record.backend_code or "",
                    "db_queries": record.db_queries or "",
                    "tech_docs": record.tech_docs or "",
                }
                st.session_state.generation_id = record.id
                st.session_state.completed = True

                display_chat_results()  # Display results without rerun
        except Exception as e:
            st.error(f"Failed to load chat: {str(e)}")

    if user_input or uploaded_file:
        results_container.empty()  # Clear previous results
        main_container.empty()  # Clear previous messages
        if user_input:
            st.session_state.messages.append(
                {"role": "user", "content": user_input, "type": "text"}
            )
        if uploaded_file:
            st.session_state.messages.append(
                {"role": "user", "content": uploaded_file, "type": "image"}
            )
        st.session_state.generating = True
        st.session_state.completed = False
        st.session_state.results = {k: "" for k in st.session_state.results}
        st.session_state.progress = {}

        generate_types = determine_generation_types(user_input or "")
        files = {"file": uploaded_file.getvalue()} if uploaded_file else {}
        data = {
            "prompt": user_input or "",
            "backend_language": backend_lang,
            "framework": framework,
            "generate_types": json.dumps(generate_types),
        }

        with st.chat_message("assistant"):
            msg_box = st.empty()
            msg_box.markdown("⚙️ Processing your request...")
            container = st.container()

        try:
            with requests.post(
                f"{BACKEND_URL}/generate-code", files=files, data=data, stream=True
            ) as r:
                r.raise_for_status()
                event = None
                for line in r.iter_lines():
                    if line:
                        line = line.decode()
                        if line.startswith("event:"):
                            event = line.split(":", 1)[1].strip()
                        elif line.startswith("data:") and event:
                            payload = json.loads(line.split(":", 1)[1].strip())
                            if event == "progress":
                                update_progress(payload["step"], payload["status"])
                                msg_box.markdown(
                                    f"⏳ {payload['step']} generation: {payload['status']}"
                                )
                            elif event in st.session_state.results:
                                st.session_state.results[event] = payload.get(
                                    "code",
                                    payload.get(
                                        "schema",
                                        payload.get(
                                            "queries", payload.get("documentation", "")
                                        ),
                                    ),
                                )
                                with container:
                                    if event == "ui_code":
                                        st.subheader("UI Code")
                                        st.code(
                                            st.session_state.results[event],
                                            language="html",
                                        )
                                    elif event == "db_schema":
                                        st.subheader("Database Schema")
                                        st.code(
                                            st.session_state.results[event],
                                            language="sql",
                                        )
                                    elif event == "backend_code":
                                        st.subheader(
                                            f"{backend_lang.capitalize()} Backend Code"
                                        )
                                        st.code(
                                            st.session_state.results[event],
                                            language=backend_lang,
                                        )
                                    elif event == "db_queries":
                                        st.subheader("Database Queries")
                                        st.code(
                                            st.session_state.results[event],
                                            language="sql",
                                        )
                                    elif event == "tech_docs":
                                        st.subheader("Technical Documentation")
                                        st.markdown(st.session_state.results[event])
                                msg_box.markdown(
                                    f"✅ {event.replace('_', ' ').title()} generated!"
                                )
                            elif event == "error":
                                st.error(
                                    f"Error: {payload['message']}\nTrace: {payload.get('traceback', 'No traceback available')}"
                                )
                                st.session_state.generating = False
                                msg_box.markdown(f"❌ Error: {payload['message']}")
                                break
                            elif event == "complete":
                                st.session_state.generation_id = payload["id"]
                                st.session_state.completed = True
                                st.session_state.generating = False
        except requests.RequestException as e:
            st.error(f"Backend error: {str(e)}\n{traceback.format_exc()}")
            msg_box.markdown("❌ Failed to connect to backend")
            st.session_state.generating = False
