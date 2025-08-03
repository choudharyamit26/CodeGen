import streamlit as st
import requests
import json
import traceback
import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
if "all_generations" not in st.session_state:
    st.session_state.all_generations = []
if "current_generation" not in st.session_state:
    st.session_state.current_generation = None
if "detected_stack" not in st.session_state:
    st.session_state.detected_stack = {"language": "python", "framework": "fastapi"}
# Add file uploader key to session state for clearing
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0


def clear_file_upload():
    """Helper function to clear file upload by changing its key"""
    st.session_state.file_uploader_key += 1


def reset_chat_state():
    """Helper function to reset all chat-related state"""
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
    clear_file_upload()  # Clear uploaded file


# Sidebar rendering
if st.session_state.sidebar_open:
    with st.sidebar:
        st.title("CodeGen")
        st.divider()
        if st.button("New Chat", use_container_width=True):
            reset_chat_state()
            st.rerun()
        st.divider()
        st.markdown("**Chats**")

        def fetch_previous_chats():
            try:
                response = requests.get(f"{BACKEND_URL}/generations")
                response.raise_for_status()
                chats = response.json()
                return chats
            except requests.HTTPError as e:
                st.error(f"Failed to fetch previous chats: {str(e)}")
                return []
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                return []

        previous_chats = fetch_previous_chats()
        selected_chat = None
        if previous_chats:
            for chat in previous_chats:
                # Create a better preview for the chat button
                prompt_preview = chat.get("prompt", "")
                if not prompt_preview or prompt_preview.strip() == "":
                    prompt_preview = "Image-based request"

                # Limit the preview length
                if len(prompt_preview) > 50:
                    button_text = f"{prompt_preview[:50]}..."
                else:
                    button_text = prompt_preview

                # Add timestamp
                timestamp = chat["created_at"][:16].replace("T", " ")
                button_label = f"{button_text} ({timestamp})"

                if st.button(
                    button_label, key=f"chat_{chat['id']}", use_container_width=True
                ):
                    selected_chat = chat["id"]
        else:
            st.info("No previous chats found.")

# Header
st.header("Ask your questions!")

# Main content container for chat messages
chat_container = st.container()

# Container for all generated outputs (displayed above input)
outputs_container = st.container()


# Function to display a single generation's results
def display_generation_results(generation, generation_index):
    query_preview = (
        generation.get("user_query", "")[:60] + "..."
        if len(generation.get("user_query", "")) > 60
        else generation.get("user_query", "")
    )
    title = (
        f"{query_preview}" if query_preview else f"Generation {generation_index + 1}"
    )

    with st.container():
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

        with st.container():
            results = generation["results"]
            backend_lang = generation.get("backend_lang", "python")

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
        for i, generation in enumerate(st.session_state.all_generations):
            display_generation_results(generation, i)

# Chat input at the bottom
input_container = st.container()
with input_container:
    # Show uploaded file status if there's one
    uploaded_file = st.file_uploader(
        "Upload an image for code generation",
        type=["jpg", "png", "jpeg"],
        key=f"file_uploader_{st.session_state.file_uploader_key}",
        help="Upload an image, then type your prompt (or just press Enter to generate code from the image)",
    )

    # Show file status
    if uploaded_file:
        st.success(
            f"✅ File uploaded: {uploaded_file.name} - Now type your prompt or press Enter to generate code"
        )

    user_input = st.chat_input(
        "What can I help with? Ask anything...", key="chat_input"
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
        r"\b(backend|api|server|python|javascript|java|go|django|flask|fastapi|express|spring|gin|core|vanilla|without framework)\b",
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


# FIX: Handle chat selection first, then handle new inputs
if selected_chat:
    try:
        response = requests.get(f"{BACKEND_URL}/generations/{selected_chat}")
        response.raise_for_status()
        record = response.json()

        # Clear existing state including uploaded files
        st.session_state.messages = []
        st.session_state.results = {
            "ui_code": record.get("ui_code", ""),
            "db_schema": record.get("db_schema", ""),
            "backend_code": record.get("backend_code", ""),
            "db_queries": record.get("db_queries", ""),
            "tech_docs": record.get("tech_docs", ""),
        }
        st.session_state.generation_id = record["id"]
        st.session_state.completed = True
        st.session_state.detected_stack = {
            "language": record.get("backend_language", "python"),
            "framework": record.get("framework", "fastapi"),
        }

        # Clear uploaded file when loading previous chat
        clear_file_upload()

        # Fix: Use the actual prompt from the record instead of generic message
        actual_prompt = record.get("prompt", "")
        display_query = actual_prompt if actual_prompt else "Image-based request"

        st.session_state.all_generations = [
            {
                "results": st.session_state.results,
                "backend_lang": st.session_state.detected_stack["language"],
                "timestamp": record["created_at"],
                "user_query": display_query,
            }
        ]
        st.rerun()
    except requests.HTTPError as e:
        st.error(f"Failed to load chat: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

# FIX: Only handle new inputs if no chat was selected AND user submitted (either with text or just Enter)
elif (
    user_input is not None
):  # This triggers when user presses Enter (with or without text)
    # Check if we have either text input or an uploaded file
    if not user_input and not uploaded_file:
        st.warning("Please either type a prompt or upload an image file.")
        st.stop()

    # Add messages to session state
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
    st.session_state.detected_stack = {"language": "python", "framework": "fastapi"}

    # Fix: Create a more descriptive query for image uploads
    if user_input and uploaded_file:
        display_query = f"{user_input} (with uploaded image: {uploaded_file.name})"
    elif user_input:
        display_query = user_input
    elif uploaded_file:
        display_query = f"Generate code from uploaded image: {uploaded_file.name}"
    else:
        display_query = "Code generation request"

    st.session_state.current_generation = {
        "results": {k: "" for k in st.session_state.results},
        "backend_lang": "python",
        "timestamp": None,
        "user_query": display_query,
    }

    generate_types = determine_generation_types(user_input or "")
    data = {
        "prompt": user_input or "",
        "generate_types": json.dumps(generate_types),
    }

    with chat_container:
        with st.chat_message("assistant"):
            msg_box = st.empty()
            msg_box.markdown("⚙️ Processing your request...")

    current_generation_placeholder = st.empty()

    try:
        if uploaded_file:
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type,
                )
            }
            response = requests.post(
                f"{BACKEND_URL}/generate-code", files=files, data=data, stream=True
            )
        else:
            response = requests.post(
                f"{BACKEND_URL}/generate-code", data=data, stream=True
            )

        response.raise_for_status()
        event = None
        for line in response.iter_lines():
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
                    elif event == "config":
                        st.session_state.detected_stack = {
                            "language": payload["backend_language"],
                            "framework": payload["framework"],
                        }
                        st.session_state.current_generation["backend_lang"] = payload[
                            "backend_language"
                        ]
                    elif event in st.session_state.results:
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
                        st.session_state.current_generation["results"][event] = content
                        with current_generation_placeholder.container():
                            st.markdown("---")
                            st.subheader("🔄 Current Generation")
                            with st.expander("Generated Code (Live)", expanded=True):
                                for key, value in st.session_state.current_generation[
                                    "results"
                                ].items():
                                    if value:
                                        if key == "ui_code":
                                            st.subheader("UI Code")
                                            st.code(value, language="html")
                                        elif key == "db_schema":
                                            st.subheader("Database Schema")
                                            st.code(value, language="sql")
                                        elif key == "backend_code":
                                            st.subheader(
                                                f"{st.session_state.detected_stack['language'].capitalize()} Backend Code"
                                            )
                                            st.code(
                                                value,
                                                language=st.session_state.detected_stack[
                                                    "language"
                                                ],
                                            )
                                        elif key == "db_queries":
                                            st.subheader("Database Queries")
                                            st.code(value, language="sql")
                                        elif key == "tech_docs":
                                            st.subheader("Technical Documentation")
                                            st.markdown(value)
                        msg_box.markdown(
                            f"✅ {event.replace('_', ' ').title()} generated!"
                        )
                    elif event == "error":
                        st.error(
                            f"Error: {payload['message']}\nTrace: {payload.get('traceback', 'No traceback available')}"
                        )
                        msg_box.markdown(f"❌ Error: {payload['message']}")
                        st.session_state.generating = False
                        break
                    elif event == "complete":
                        st.session_state.generation_id = payload["id"]
                        st.session_state.completed = True
                        st.session_state.generating = False
                        st.session_state.all_generations.append(
                            st.session_state.current_generation.copy()
                        )
                        st.session_state.current_generation = None
                        current_generation_placeholder.empty()
                        msg_box.markdown("✅ Generation completed!")
                        # Clear uploaded file after successful generation
                        clear_file_upload()
                        st.rerun()
    except requests.HTTPError as e:
        st.error(f"Backend error: {str(e)}")
        try:
            error_response = response.json()
            st.error(f"Error details: {error_response}")
        except:
            st.error(f"Response: {response.text}")
        msg_box.markdown(f"❌ Backend error: {response.text}")
        st.session_state.generating = False
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        msg_box.markdown(f"❌ Unexpected error: {str(e)}")
        st.session_state.generating = False
