"""The mutation operator: one OpenRouter call, and the key handling around it.

Slide 6 of the lecture is the reason this file is so short. Classical genetic programming
perturbs a syntax tree at random — valid code, semantically blind, and it needs enormous
populations to get anywhere. Here the mutation operator is a language model that has read
everything anyone has written about neural networks. It is a *prior over useful directions*.

That is the whole upgrade. Everything else in a system like AlphaEvolve is plumbing around
this one substitution.
"""
from __future__ import annotations

import os

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "google/gemini-2.5-flash"   # cheap and fast: a search makes many calls
DEFAULT_TEMPERATURE = 0.9                   # high on purpose — see `complete()`


def get_api_key(explicit: str | None = None) -> str:
    """Colab secret, then environment. Raises rather than limping on with no key."""
    if explicit:
        return explicit.strip()
    try:
        from google.colab import userdata
        key = userdata.get("OPENROUTER_API_KEY")
        if key:
            return key.strip()
    except Exception:
        pass
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "No OpenRouter API key found.\n"
            "  · In Colab: open the 🔑 Secrets panel, add OPENROUTER_API_KEY, and toggle "
            "notebook access on.\n"
            "  · Locally:  export OPENROUTER_API_KEY=sk-or-...\n"
            "Get a key at https://openrouter.ai/keys")
    return key


def _client(api_key: str | None = None):
    from openai import OpenAI
    return OpenAI(api_key=get_api_key(api_key), base_url=BASE_URL, timeout=90, max_retries=2)


def complete(prompt: str, system: str = "", model: str | None = None,
             temperature: float = DEFAULT_TEMPERATURE, api_key: str | None = None) -> str:
    """One completion. The temperature is a search parameter, not a style setting.

    At temperature 0 every child of the same parent is the same child, and the search
    collapses to a single lineage. The randomness *is* the exploration budget — slide 6's
    point that hallucination stops being a failure mode once a scoreboard is filtering the
    output.

    Args:
        prompt: the user message. In this exercise, a parent program plus scored rivals.
        system: the system message — the standing instructions for every mutation.
        model: OpenRouter model id. Defaults to a cheap fast one.
        temperature: sampling temperature.
        api_key: overrides the Colab secret / environment lookup.

    Returns:
        The model's reply text.
    """
    resp = _client(api_key).chat.completions.create(
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        messages=([{"role": "system", "content": system}] if system else [])
                 + [{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def check_api_key(api_key: str | None = None, model: str | None = None) -> str:
    """One cheap call, so a bad key fails here rather than eight generations in."""
    complete("Reply with the single word: ready", model=model, temperature=0, api_key=api_key)
    return f"OpenRouter reachable · model {model or DEFAULT_MODEL} ✅"
