"""Service for analyzing image quality for real-time camera feedback."""

import logging
from google.cloud import vision

logger = logging.getLogger(__name__)

class ImageAnalysisService:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient()

    async def analyze_quality(self, content: bytes) -> dict:
        """Analyze image quality (blur, brightness, orientation)."""
        try:
            image = vision.Image(content=content)
            
            # Request image properties and text detection (to check for content)
            features = [
                {"type_": vision.Feature.Type.IMAGE_PROPERTIES},
                {"type_": vision.Feature.Type.TEXT_DETECTION},
            ]
            
            # Using synchronous client for now, wrapping in thread if needed
            # For a "real-time" feel, we want this to be fast.
            response = self.client.annotate_image({
                "image": image,
                "features": features,
            })
            
            if response.error.message:
                raise Exception(response.error.message)

            props = response.image_properties_annotation
            text = response.text_annotations
            
            # Basic heuristics
            has_text = len(text) > 0
            
            # Check for dominant colors to estimate brightness
            # (Simplified logic: average of RGB components)
            brightness = 0.5
            if props.dominant_colors.colors:
                color = props.dominant_colors.colors[0].color
                brightness = (color.red + color.green + color.blue) / (3 * 255)

            status = "good"
            feedback = "Looks great! Keep it still."
            
            if not has_text:
                status = "poor"
                feedback = "I don't see any text. Try moving closer."
            elif brightness < 0.3:
                status = "poor"
                feedback = "It's a bit dark. Try turning on a light."
            elif brightness > 0.9:
                status = "poor"
                feedback = "It's a bit too bright. Watch out for glare."

            return {
                "status": status,
                "feedback": feedback,
                "has_text": has_text,
                "brightness": round(brightness, 2),
            }
        except Exception:
            logger.exception("Image analysis failed")
            return {
                "status": "error",
                "feedback": "I'm having trouble seeing that. Try again?",
            }

def get_image_analysis_service() -> ImageAnalysisService:
    return ImageAnalysisService()
