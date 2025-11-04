import os
from typing import Optional

import streamlit as st

from src.gemini_assistant import GeminiAssistant


def _init_assistant(api_key: Optional[str]) -> Optional[GeminiAssistant]:
    if not api_key:
        return None
    try:
        return GeminiAssistant(api_key=api_key.strip())
    except RuntimeError as exc:
        st.error(str(exc))
        return None


st.set_page_config(page_title="Gemini Personal Assistant", page_icon="🤖", layout="wide")
st.title("Gemini Personal Assistant")

if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "").strip()

if "assistant" not in st.session_state:
    st.session_state.assistant = _init_assistant(st.session_state.api_key)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.header("Setup")
    new_key = st.text_input("Google API key", type="password", value=st.session_state.api_key)
    if st.button("Apply key"):
        sanitized_key = new_key.strip()
        st.session_state.api_key = sanitized_key
        st.session_state.assistant = _init_assistant(sanitized_key)
        st.session_state.chat_history = []
        if st.session_state.assistant:
            st.success("API key updated and assistant ready.")

assistant: Optional[GeminiAssistant] = st.session_state.assistant

if not assistant:
    st.info("Add your Google API key in the sidebar to start chatting.")
    st.stop()

chat_tab, image_tab = st.tabs(["Chat", "Image Studio"])

with chat_tab:
    st.subheader("Multimodal chat")

    with st.form("chat_form", clear_on_submit=False):
        user_prompt = st.text_area("Message", placeholder="Ask for your agenda, request a fact, or send an image for analysis.")
        uploaded_image = st.file_uploader("Optional image (PNG/JPEG)", type=["png", "jpg", "jpeg"])
        send = st.form_submit_button("Send")

    if send:
        if not user_prompt and uploaded_image is None:
            st.warning("Provide a message, an image, or both.")
        else:
            image_bytes = uploaded_image.read() if uploaded_image else None
            mime = uploaded_image.type if uploaded_image else "image/png"
            response = assistant.chat(user_prompt, image_bytes=image_bytes, mime_type=mime)
            st.session_state.chat_history.append(("user", user_prompt, image_bytes, mime))
            st.session_state.chat_history.append(("assistant", response, None, None))

    if st.button("Reset conversation"):
        assistant.reset()
        st.session_state.chat_history = []
        st.success("Conversation cleared.")

    for role, text, image_bytes, mime in st.session_state.chat_history:
        if role == "user":
            with st.chat_message("user"):
                st.markdown(text or "(image only message)")
                if image_bytes:
                    st.image(image_bytes, caption="User upload", use_column_width=True)
        else:
            with st.chat_message("assistant"):
                st.markdown(text)

with image_tab:
    st.subheader("Image generation")
    image_prompt = st.text_area("Describe the image you want to create.", key="image_prompt")
    aspect_ratio = st.selectbox(
        "Aspect ratio",
        options=["1:1", "16:9", "9:16", "3:2"],
        index=0,
    )
    if st.button("Generate image"):
        if not image_prompt:
            st.warning("Add a description first.")
        else:
            try:
                image_bytes = assistant.generate_image(image_prompt, aspect_ratio=aspect_ratio)
                st.image(image_bytes, caption="Generated image", use_column_width=True)
                st.download_button(
                    "Download image",
                    data=image_bytes,
                    file_name="gemini_image.png",
                    mime="image/png",
                )
            except Exception as exc:  # pragma: no cover - runtime feedback
                st.error(f"Image generation failed: {exc}")
