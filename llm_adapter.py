"""Optional OpenAI-compatible adapter for replacing deterministic demo text generation."""

from __future__ import annotations

import os
from typing import Any


def ask_model(prompt: str, system: str = "You are a precise junior AI engineer.") -> str:
    """Call an OpenAI-compatible endpoint when credentials are configured."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt before using the live adapter") from exc
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY to use the live adapter")
    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("MODEL", "gpt-5-mini"),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        max_completion_tokens=800,
    )
    return response.choices[0].message.content or ""
