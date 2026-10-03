from typing import Any


def content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = content_to_text(item)
            if text:
                parts.append(text)
        return "".join(parts)
    if isinstance(content, dict):
        for key in ("text", "content", "value"):
            if key in content:
                return content_to_text(content.get(key))
        return ""
    return str(content)


def normalize_choices_text(choices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for choice in choices or []:
        choice_copy = dict(choice)
        message = dict(choice_copy.get("message") or {})
        if message:
            message["content"] = content_to_text(message.get("content"))
            choice_copy["message"] = message
        normalized.append(choice_copy)
    return normalized


def extract_response_text(data: dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return ""

    for key in ("response", "output_text", "text", "content"):
        if key in data:
            text = content_to_text(data.get(key))
            if text:
                return text

    output = data.get("output")
    if isinstance(output, list):
        text = content_to_text(output)
        if text:
            return text

    return ""
