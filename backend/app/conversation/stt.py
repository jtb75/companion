import logging

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_data: bytes) -> str | None:
    """Transcribe audio using Google Cloud Speech-to-Text.

    Returns transcript text or None if STT is unavailable.
    """
    try:
        from google.cloud import speech

        client = speech.SpeechAsyncClient()
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            model="latest_long",
            enable_automatic_punctuation=True,
        )
        response = await client.recognize(config=config, audio=audio)
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            if confidence < 0.6:
                return None  # too low confidence
            return transcript
        return None
    except Exception:
        logger.warning("STT unavailable")
        return None
