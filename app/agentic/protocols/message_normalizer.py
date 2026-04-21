from __future__ import annotations


def normalize_chat_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Normalize provider chat messages for deterministic role sequencing.

    Rules:
    - Merge all system content into one leading system message.
    - Merge consecutive turns that share the same role.
    - Preserve relative order of non-system turns.
    """
    system_parts: list[str] = []
    normalized: list[dict[str, str]] = []

    for msg in messages:
        role = str(msg.get("role") or "").strip()
        content = str(msg.get("content") or "").strip()
        if not role:
            continue

        if role == "system":
            if content:
                system_parts.append(content)
            continue

        if normalized and normalized[-1].get("role") == role:
            prev = str(normalized[-1].get("content") or "").strip()
            if prev and content:
                normalized[-1]["content"] = f"{prev}\n\n{content}"
            elif content:
                normalized[-1]["content"] = content
            continue

        normalized.append({"role": role, "content": content})

    if system_parts:
        normalized = [{"role": "system", "content": "\n\n".join(system_parts)}] + normalized

    return normalized
