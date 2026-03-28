import logging

logger = logging.getLogger(__name__)

VOICE_PROFILES = {
    "warm": {
        "label": "Warm",
        "description": "Friendly and gentle",
        "tts_config": {
            "voice_name": "en-US-Neural2-C",
            "pitch": -1.0,
            "speaking_rate": 0.92,
        },
    },
    "calm": {
        "label": "Calm",
        "description": "Steady and relaxed",
        "tts_config": {
            "voice_name": "en-US-Neural2-A",
            "pitch": -2.0,
            "speaking_rate": 0.88,
        },
    },
    "bright": {
        "label": "Bright",
        "description": "Upbeat and cheerful",
        "tts_config": {
            "voice_name": "en-US-Neural2-F",
            "pitch": 1.0,
            "speaking_rate": 1.0,
        },
    },
    "clear": {
        "label": "Clear",
        "description": "Simple and direct",
        "tts_config": {
            "voice_name": "en-US-Neural2-D",
            "pitch": 0.0,
            "speaking_rate": 0.95,
        },
    },
}


async def synthesize_speech(
    text: str, voice_id: str = "warm"
) -> bytes | None:
    """Convert text to speech using Google Cloud TTS.

    Returns audio bytes (MP3) or None if TTS is unavailable.
    """
    profile = VOICE_PROFILES.get(voice_id, VOICE_PROFILES["warm"])
    config = profile["tts_config"]

    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechAsyncClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=config["voice_name"],
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=config.get("pitch", 0.0),
            speaking_rate=config.get("speaking_rate", 1.0),
        )
        response = await client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return response.audio_content
    except Exception:
        logger.warning("TTS unavailable, returning text only")
        return None
