"""
TTS Service — Text-to-Speech synthesis.
Supports ElevenLabs (primary) and OpenAI TTS (fallback).
Returns audio as base64-encoded MP3 string.
"""

import os
import base64
import requests
from openai import OpenAI


def synthesize_speech(text: str) -> dict:
    """
    Convert text to speech audio.
    Tries ElevenLabs first, falls back to OpenAI TTS.

    Args:
        text: The text to convert to speech.

    Returns:
        dict with keys:
          - audio_base64 (str): Base64-encoded MP3 audio.
          - provider (str): Which TTS provider was used.
          - error (str | None): Error message if synthesis failed.
    """
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Try ElevenLabs first
    if elevenlabs_key:
        result = _elevenlabs_tts(text, elevenlabs_key)
        if result.get("audio_base64"):
            return result

    # Fall back to OpenAI TTS
    if openai_key:
        result = _openai_tts(text, openai_key)
        if result.get("audio_base64"):
            return result

    return {
        "audio_base64": None,
        "provider": None,
        "error": "No TTS provider configured. Add ELEVENLABS_API_KEY or OPENAI_API_KEY to .env",
    }


def _elevenlabs_tts(text: str, api_key: str) -> dict:
    """Synthesize speech using ElevenLabs API."""
    try:
        # Rachel voice — clear and natural
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()

        audio_b64 = base64.b64encode(response.content).decode("utf-8")
        return {"audio_base64": audio_b64, "provider": "elevenlabs", "error": None}

    except Exception as e:
        return {"audio_base64": None, "provider": "elevenlabs", "error": str(e)}


def _openai_tts(text: str, api_key: str) -> dict:
    """Synthesize speech using OpenAI TTS API."""
    try:
        client = OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model="tts-1",
            voice=os.getenv("OPENAI_TTS_VOICE", "nova"),
            input=text,
            response_format="mp3",
        )
        audio_b64 = base64.b64encode(response.content).decode("utf-8")
        return {"audio_base64": audio_b64, "provider": "openai", "error": None}

    except Exception as e:
        return {"audio_base64": None, "provider": "openai", "error": str(e)}
