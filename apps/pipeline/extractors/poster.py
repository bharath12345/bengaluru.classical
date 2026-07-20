from apps.pipeline.extractors.gemini_client import GeminiClient

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "genre": {"type": "string"},
        "start_at": {"type": "string"},
        "venue_name": {"type": "string"},
        "artist_names": {"type": "array", "items": {"type": "string"}},
        "description": {"type": "string"},
    },
}


def extract_from_poster(client: GeminiClient, image_bytes: bytes) -> dict:
    return client.extract_structured(
        "Extract classical concert details from this poster image.",
        EVENT_SCHEMA,
        image=image_bytes,
    )


def extract_from_html_text(client: GeminiClient, text: str) -> dict:
    return client.extract_structured(
        f"Extract classical concert details from this page text:\n\n{text[:8000]}",
        EVENT_SCHEMA,
    )
