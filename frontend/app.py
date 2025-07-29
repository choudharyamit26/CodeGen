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
# New session state to store all generations in order
if "all_generations" not in st.session_state:
    st.session_state.all_generations = []
if "current_generation" not in st.session_state:
    st.session_state.current_generation = None

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
            st.session_state.all_generations = []
            st.session_state.current_generation = None
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

# Main content container for chat messages
chat_container = st.container()

# Container for all generated outputs (displayed above input)
outputs_container = st.container()


# Function to display a single generation's results
def display_generation_results(generation, generation_index):
    # Create the title with user query
    query_preview = (
        generation.get("user_query", "")[:60] + "..."
        if len(generation.get("user_query", "")) > 60
        else generation.get("user_query", "")
    )
    title = (
        f"{query_preview}" if query_preview else f"Generation {generation_index + 1}"
    )

    # Create a styled container/card
    with st.container():
        # Header with query in a colored container
        st.markdown(
            f"""
        <div style="
            background-color: #262730;
            padding: 12px 16px;
            border-radius: 8px;
            border-left: 4px solid #ff4b4b;
            margin-bottom: 16px;
        ">
            <h4 style="margin: 0; color: white; font-size: 16px;">
                🔹 {title}
            </h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Results in a card container
        with st.container():
            results = generation["results"]
            backend_lang = generation.get("backend_lang", "python")

            # Add some padding and background styling
            st.markdown(
                """
            <style>
            .generation-card {
                background-color: #1e1e1e;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #333;
            }
            </style>
            """,
                unsafe_allow_html=True,
            )

            if results["ui_code"]:
                st.subheader("UI Code")
                st.code(results["ui_code"], language="html")
            if results["db_schema"]:
                st.subheader("Database Schema")
                st.code(results["db_schema"], language="sql")
            if results["backend_code"]:
                st.subheader(f"{backend_lang.capitalize()} Backend Code")
                st.code(results["backend_code"], language=backend_lang)
            if results["db_queries"]:
                st.subheader("Database Queries")
                st.code(results["db_queries"], language="sql")
            if results["tech_docs"]:
                st.subheader("Technical Documentation")
                st.markdown(results["tech_docs"])

        # Add a separator between generations
        if generation_index < len(st.session_state.all_generations) - 1:
            st.markdown(
                "<hr style='margin: 30px 0; border: 1px solid #333;'>",
                unsafe_allow_html=True,
            )


# Display all generations in the outputs container
with outputs_container:
    if st.session_state.all_generations:
        st.markdown("---")
        st.subheader("Generated Code")
        # Display generations in chronological order (oldest first)
        for i, generation in enumerate(st.session_state.all_generations):
            display_generation_results(generation, i)

# Chat input at the bottom
input_container = st.container()
with input_container:
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

                # Load as a single generation
                st.session_state.all_generations = [
                    {
                        "results": st.session_state.results,
                        "backend_lang": backend_lang,
                        "timestamp": record.created_at,
                        "user_query": record.prompt or "Image-based request",
                    }
                ]
                st.rerun()
        except Exception as e:
            st.error(f"Failed to load chat: {str(e)}")

    if user_input or uploaded_file:
        # Add user message to chat history
        if user_input:
            st.session_state.messages.append(
                {"role": "user", "content": user_input, "type": "text"}
            )
        if uploaded_file:
            st.session_state.messages.append(
                {"role": "user", "content": uploaded_file, "type": "image"}
            )

        # Initialize new generation
        st.session_state.generating = True
        st.session_state.completed = False
        st.session_state.results = {k: "" for k in st.session_state.results}
        st.session_state.progress = {}

        # Create new current generation
        st.session_state.current_generation = {
            "results": {k: "" for k in st.session_state.results},
            "backend_lang": backend_lang,
            "timestamp": None,
            "user_query": user_input or "Image-based request",
        }

        generate_types = determine_generation_types(user_input or "")
        files = {"file": uploaded_file.getvalue()} if uploaded_file else {}
        data = {
            "prompt": user_input or "",
            "backend_language": backend_lang,
            "framework": framework,
            "generate_types": json.dumps(generate_types),
        }

        # Add assistant message placeholder
        with chat_container:
            with st.chat_message("assistant"):
                msg_box = st.empty()
                msg_box.markdown("⚙️ Processing your request...")

        # Create a placeholder for the current generation in outputs
        current_generation_placeholder = st.empty()

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
                                # Update both session results and current generation
                                content = payload.get(
                                    "code",
                                    payload.get(
                                        "schema",
                                        payload.get(
                                            "queries", payload.get("documentation", "")
                                        ),
                                    ),
                                )
                                st.session_state.results[event] = content
                                st.session_state.current_generation["results"][
                                    event
                                ] = content

                                # Display current generation above input
                                with current_generation_placeholder.container():
                                    st.markdown("---")
                                    st.subheader("🔄 Current Generation")
                                    with st.expander(
                                        "Generated Code (Live)", expanded=True
                                    ):
                                        if event == "ui_code" and content:
                                            st.subheader("UI Code")
                                            st.code(content, language="html")
                                        elif event == "db_schema" and content:
                                            st.subheader("Database Schema")
                                            st.code(content, language="sql")
                                        elif event == "backend_code" and content:
                                            st.subheader(
                                                f"{backend_lang.capitalize()} Backend Code"
                                            )
                                            st.code(content, language=backend_lang)
                                        elif event == "db_queries" and content:
                                            st.subheader("Database Queries")
                                            st.code(content, language="sql")
                                        elif event == "tech_docs" and content:
                                            st.subheader("Technical Documentation")
                                            st.markdown(content)

                                        # Show all completed parts of current generation
                                        for (
                                            key,
                                            value,
                                        ) in st.session_state.current_generation[
                                            "results"
                                        ].items():
                                            if (
                                                value and key != event
                                            ):  # Don't duplicate the current event
                                                if key == "ui_code":
                                                    st.subheader("UI Code")
                                                    st.code(value, language="html")
                                                elif key == "db_schema":
                                                    st.subheader("Database Schema")
                                                    st.code(value, language="sql")
                                                elif key == "backend_code":
                                                    st.subheader(
                                                        f"{backend_lang.capitalize()} Backend Code"
                                                    )
                                                    st.code(
                                                        value, language=backend_lang
                                                    )
                                                elif key == "db_queries":
                                                    st.subheader("Database Queries")
                                                    st.code(value, language="sql")
                                                elif key == "tech_docs":
                                                    st.subheader(
                                                        "Technical Documentation"
                                                    )
                                                    st.markdown(value)

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

                                # Add completed generation to all_generations list
                                st.session_state.all_generations.append(
                                    st.session_state.current_generation.copy()
                                )
                                st.session_state.current_generation = None

                                # Clear the current generation placeholder
                                current_generation_placeholder.empty()

                                msg_box.markdown("✅ Generation completed!")
                                st.rerun()  # Refresh to show the completed generation in the outputs container

        except requests.RequestException as e:
            st.error(f"Backend error: {str(e)}\n{traceback.format_exc()}")
            msg_box.markdown("❌ Failed to connect to backend")
            st.session_state.generating = False
