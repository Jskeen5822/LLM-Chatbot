from __future__ import annotations

from typing import Any, Callable, Dict, List

ToolHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


def build_tool_spec() -> List[Dict[str, Any]]:
    """Return the tool declarations the Gemini model can call."""

    weather_parameters = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City and state (or country) to get the short-term forecast for.",
            },
            "unit": {
                "type": "string",
                "description": "Temperature unit, either 'fahrenheit' or 'celsius'.",
                "enum": ["fahrenheit", "celsius"],
            },
        },
        "required": ["location"],
    }

    calendar_parameters = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "ISO-8601 date to review upcoming events for (YYYY-MM-DD).",
            }
        },
        "required": ["date"],
    }

    reminder_parameters = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Reminder text (<= 120 characters).",
            },
            "due_time": {
                "type": "string",
                "description": "ISO-8601 timestamp indicating when the reminder should fire.",
            },
        },
        "required": ["summary", "due_time"],
    }

    wikipedia_parameters = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Short topic or entity name to look up on Wikipedia.",
            }
        },
        "required": ["topic"],
    }

    email_parameters = {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Recipient name or email to personalize the greeting.",
            },
            "subject": {
                "type": "string",
                "description": "Concise subject line the email should address.",
            },
            "outline": {
                "type": "string",
                "description": "Bullet list or short description describing the talking points.",
            },
        },
        "required": ["recipient", "subject", "outline"],
    }

    return [
        {
            "function_declarations": [
                {
                    "name": "get_weather_forecast",
                    "description": "Returns a concise 12-hour weather forecast for the provided location.",
                    "parameters": weather_parameters,
                },
                {
                    "name": "list_calendar_agenda",
                    "description": "Returns upcoming events for the requested date.",
                    "parameters": calendar_parameters,
                },
                {
                    "name": "create_reminder",
                    "description": "Stores a reminder with the provided summary and due time.",
                    "parameters": reminder_parameters,
                },
                {
                    "name": "search_public_info",
                    "description": "Fetches a concise factual summary for the requested topic from Wikipedia.",
                    "parameters": wikipedia_parameters,
                },
                {
                    "name": "draft_email_outline",
                    "description": "Returns a structured email draft using the provided subject outline.",
                    "parameters": email_parameters,
                },
            ]
        }
    ]


TOOL_NAMES = {
    "get_weather_forecast",
    "list_calendar_agenda",
    "create_reminder",
    "search_public_info",
    "draft_email_outline",
}
