from __future__ import annotations

import base64
import io
import os
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import google.generativeai as genai
import requests
from dateutil import parser as date_parser

from .tools import TOOL_NAMES, build_tool_spec


@dataclass
class AssistantState:
    reminders: List[Dict[str, Any]] = field(default_factory=list)
    calendar_seed: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.calendar_seed:
            today = datetime.utcnow().date()
            self.calendar_seed = {
                today.isoformat(): [
                    {
                        "title": "Stand-up with product team",
                        "time": "09:30",
                        "location": "Zoom",
                        "notes": "Share progress on the onboarding flow prototype.",
                    },
                    {
                        "title": "Gym session",
                        "time": "17:45",
                        "location": "Local fitness center",
                        "notes": "Strength day - focus on posterior chain.",
                    },
                ],
                (today + timedelta(days=1)).isoformat(): [
                    {
                        "title": "Client status update",
                        "time": "13:00",
                        "location": "Teams",
                        "notes": "Review Q4 roadmap and confirm deliverables.",
                    }
                ],
            }


class GeminiAssistant:
    """Wrapper around Google Gemini for a multi-modal personal assistant."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        image_model_name: str = "imagen-3.0-light",
    ) -> None:
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")

        genai.configure(api_key=key)
        self._text_model = genai.GenerativeModel(
            model_name=model_name,
            tools=build_tool_spec(),
            system_instruction=textwrap.dedent(
                """
                You are a proactive personal assistant who can call tools when they can provide
                more precise information than guessing. Stay concise, cite tool results, and
                never fabricate tool data. When you receive image inputs, incorporate visual
                details in the answer.
                """
            ).strip(),
        )
        self._image_model = genai.GenerativeModel(model_name=image_model_name)
        self._state = AssistantState()
        self._history: List[Dict[str, Any]] = []

    # --- Public API -----------------------------------------------------
    def reset(self) -> None:
        """Clear the running conversation history."""

        self._history.clear()

    def chat(self, prompt: str, image_bytes: Optional[bytes] = None, mime_type: str = "image/png") -> str:
        """Send a prompt (and optional image) to Gemini and return the response text."""

        if not prompt and image_bytes is None:
            raise ValueError("Provide text, an image, or both.")

        user_message = self._build_user_message(prompt, image_bytes, mime_type)
        self._history.append(user_message)
        response = self._generate_until_complete()
        return self._parts_to_text(response.get("parts", []))

    def analyze_image(self, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Shortcut for one-off image reasoning queries."""

        self.reset()
        return self.chat(prompt=prompt, image_bytes=image_bytes, mime_type=mime_type)

    def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> bytes:
        """Use Imagen to generate an image for the provided prompt."""

        # Gemini expects aspect ratio inside a tool config for image generation.
        tool_config = {
            "image_generation_config": {"aspect_ratio": aspect_ratio}
        }
        resp = self._image_model.generate_content(
            prompt,
            generation_config={"response_mime_type": "image/png"},
            tool_config=tool_config,
        )

        parts = resp.candidates[0].content.parts
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if not inline:
                continue
            data = inline.get("data") if isinstance(inline, dict) else getattr(inline, "data", None)
            if not data:
                continue
            if isinstance(data, bytes):
                return data
            return base64.b64decode(data)

        raise RuntimeError("Image generation returned no image data.")

    # --- Internal helpers -----------------------------------------------
    def _generate_until_complete(self) -> Dict[str, Any]:
        """Call Gemini repeatedly until no more tool calls are requested."""

        while True:
            response = self._text_model.generate_content(
                contents=self._history,
            )

            candidate = response.candidates[0]
            model_message = self._content_to_dict(candidate.content)
            self._history.append(model_message)

            function_calls = self._extract_function_calls(model_message)
            if not function_calls:
                return model_message

            for function_call in function_calls:
                tool_response = self._dispatch_tool_call(function_call)
                tool_message = {
                    "role": "tool",
                    "parts": [
                        {
                            "function_response": {
                                "name": function_call["name"],
                                "response": tool_response,
                            }
                        }
                    ],
                }
                self._history.append(tool_message)

    def _dispatch_tool_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        name = function_call.get("name")
        if name not in TOOL_NAMES:
            return {"error": f"Tool '{name}' is not available."}

        handlers = {
            "get_weather_forecast": self._tool_get_weather_forecast,
            "list_calendar_agenda": self._tool_list_calendar_agenda,
            "create_reminder": self._tool_create_reminder,
            "search_public_info": self._tool_search_public_info,
            "draft_email_outline": self._tool_draft_email_outline,
        }

        handler = handlers[name]
        arguments = function_call.get("args", {})
        if not isinstance(arguments, dict):
            # Convert proto Struct into dict-like if needed.
            arguments = dict(arguments)

        return handler(arguments)

    def _tool_get_weather_forecast(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        location = arguments.get("location", "").strip()
        unit = (arguments.get("unit") or "fahrenheit").lower()
        if unit not in {"fahrenheit", "celsius"}:
            unit = "fahrenheit"

        if not location:
            return {"error": "Missing location."}

        query = location.replace(" ", "%20")
        try:
            resp = requests.get(f"https://wttr.in/{query}?format=j1", timeout=6)
            resp.raise_for_status()
            payload = resp.json()
            condition = payload["current_condition"][0]
            summary = condition["weatherDesc"][0]["value"]
            temp_c = float(condition.get("temp_C", 0))
            temp_f = float(condition.get("temp_F", 0))
            humidity = condition.get("humidity", "?")
            feels_c = float(condition.get("FeelsLikeC", temp_c))
            feels_f = float(condition.get("FeelsLikeF", temp_f))
            area_name = payload.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", location)

            temp = temp_f if unit == "fahrenheit" else temp_c
            feels_like = feels_f if unit == "fahrenheit" else feels_c
            unit_symbol = "°F" if unit == "fahrenheit" else "°C"

            return {
                "location": area_name,
                "summary": summary,
                "temperature": f"{temp:.0f}{unit_symbol}",
                "feels_like": f"{feels_like:.0f}{unit_symbol}",
                "humidity": f"{humidity}%",
                "source": "wttr.in",
            }
        except Exception as exc:  # pragma: no cover - network failures
            return {
                "location": location,
                "error": f"Weather provider unavailable: {exc}",
            }

    def _tool_list_calendar_agenda(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        date_str = arguments.get("date")
        if not date_str:
            return {"error": "Provide a date in YYYY-MM-DD format."}

        try:
            parsed = date_parser.parse(date_str).date()
        except (ValueError, TypeError) as exc:
            return {"error": f"Invalid date: {exc}"}

        agenda = self._state.calendar_seed.get(parsed.isoformat(), [])
        return {"date": parsed.isoformat(), "events": agenda}

    def _tool_create_reminder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        summary = arguments.get("summary", "").strip()
        due_time_raw = arguments.get("due_time")
        if not summary:
            return {"error": "Reminder summary cannot be empty."}
        if not due_time_raw:
            return {"error": "Provide a due_time in ISO-8601 format."}

        try:
            due_time = date_parser.parse(due_time_raw)
        except (ValueError, TypeError) as exc:
            return {"error": f"Invalid due_time: {exc}"}

        reminder = {
            "summary": summary,
            "due_time": due_time.isoformat(),
        }
        self._state.reminders.append(reminder)
        return {"status": "stored", "reminder": reminder, "total": len(self._state.reminders)}

    def _tool_search_public_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        topic = arguments.get("topic", "").strip()
        if not topic:
            return {"error": "Topic cannot be empty."}

        endpoint = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic.replace(" ", "%20")
        try:
            resp = requests.get(endpoint, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            summary = data.get("extract") or data.get("description")
            return {
                "title": data.get("title", topic),
                "summary": summary,
                "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                "source": "wikipedia",
            }
        except Exception as exc:  # pragma: no cover - network failures
            return {
                "topic": topic,
                "error": f"Wikipedia lookup failed: {exc}",
            }

    def _tool_draft_email_outline(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        recipient = arguments.get("recipient", "there").strip() or "there"
        subject = arguments.get("subject", "Quick update").strip() or "Quick update"
        outline_raw = arguments.get("outline", "").strip()
        bullets = [line.strip("-• ") for line in outline_raw.splitlines() if line.strip()]

        body_paragraphs = [
            f"Hi {recipient},",
            f"I hope you're doing well. I'm reaching out about {subject.lower()}.",
        ]
        if bullets:
            body_paragraphs.append("Here are the key points:")
            for bullet in bullets:
                body_paragraphs.append(f"- {bullet}")
        body_paragraphs.append("Let me know if you have any questions or need more detail.")
        body_paragraphs.append("Best,\nYour Assistant")

        return {
            "subject": subject,
            "body": "\n".join(body_paragraphs),
        }

    # --- Utility --------------------------------------------------------
    def _build_user_message(
        self,
        prompt: str,
        image_bytes: Optional[bytes],
        mime_type: str,
    ) -> Dict[str, Any]:
        parts: List[Dict[str, Any]] = []
        if prompt:
            parts.append({"text": prompt})
        if image_bytes is not None:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                }
            )
        return {"role": "user", "parts": parts}

    def _extract_function_calls(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        for part in message.get("parts", []):
            fn_call = part.get("function_call")
            if fn_call:
                calls.append(fn_call)
        return calls

    def _parts_to_text(self, parts: Iterable[Dict[str, Any]]) -> str:
        texts = [part.get("text", "") for part in parts if "text" in part]
        return "\n".join(filter(None, (text.strip() for text in texts)))

    def _content_to_dict(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        # The SDK returns a proto-backed object; rely on its built-in to_dict when available.
        if hasattr(content, "to_dict"):
            return content.to_dict()
        raise TypeError(f"Unsupported content representation: {type(content)!r}")
