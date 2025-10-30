# Gemini Personal Assistant

A small personal assistant web app powered by Google Gemini. The tool demonstrates:

- Conversational text chat with function/tool calling (weather, reminders, calendar, fact lookup, email drafting)
- Multimodal reasoning over user-supplied images
- Imagen-based image generation with downloadable results

## Features

- **Tool calling:** Five function tools (`get_weather_forecast`, `list_calendar_agenda`, `create_reminder`, `search_public_info`, `draft_email_outline`) enable accurate, grounded responses for common assistant tasks. Gemini may call any tool as needed during a chat turn.
- **Image understanding:** Upload a PNG or JPEG and ask questions about it; Gemini will incorporate visual details into the reply.
- **Image generation:** Describe any scene and generate a synthetic image via Imagen (`imagen-3.0-light`).
- **Streamlit UI:** Clean two-tab layout for chat and image generation, chat-style history, and one-click image downloads.

## Prerequisites

1. Python 3.10+
2. A Google AI Studio API key with Gemini access. [Create one here](https://aistudio.google.com/app/apikey) if you have not already.

## Installation

```powershell
# Clone
cd <your_working_directory>
git clone https://github.com/Jskeen5822/LLM-Chatbot.git
cd LLM-Chatbot

# (Recommended) create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

Set your API key (replace `YOUR_KEY`):

```powershell
$env:GOOGLE_API_KEY = "YOUR_KEY"
```

## Running the app

```powershell
streamlit run streamlit_app.py
```

- Open the provided local URL in your browser.
- If you did not export `GOOGLE_API_KEY`, paste it in the sidebar "Setup" section and click **Apply key**.
- Use the **Chat** tab to talk to the assistant. Attach an image to trigger multimodal reasoning.
- Use the **Image Studio** tab to generate imagery; download results via the provided button.

## Suggested demo flow (for video submission)

1. Mention that the app is a Gemini-powered personal assistant with tool calling, image reasoning, and image creation.
2. Show a chat turn that triggers a tool (e.g., "What is the weather in Paris?" → inspect result mentioning wttr.in).
3. Ask for the day's agenda (calendar tool) and create a reminder.
4. Upload an image (e.g., a photo or a screenshot) and ask the assistant to describe or reason about it.
5. Switch to **Image Studio**, generate a creative image, and download it.
6. Close by pointing viewers to the public GitHub repository (this project) for source code.

Record the walkthrough with your preferred screen recorder (e.g., Xbox Game Bar on Windows: `Win + G`).

## Repository structure

```
├── requirements.txt
├── streamlit_app.py
└── src
    └── gemini_assistant
        ├── __init__.py
        ├── assistant.py
        └── tools.py
```

## Troubleshooting

- **API key errors:** Ensure the key is valid and that the Google AI Studio project has access to Gemini and Imagen models.
- **Tool failures:** The weather and Wikipedia tools call public endpoints. If you are offline, Gemini will receive the reported error message and should fall back gracefully.
- **Image generation issues:** Some prompts may be blocked by safety filters; try a different description.

## License

This project is released under the MIT License. Feel free to fork and extend it for your own assistant experiments.
