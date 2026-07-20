from apps.events.models import Event
from apps.sources.models import Source


def compute_confidence(candidate: dict, source: Source, dedup_collision: bool) -> tuple[float, str]:
    """
    Compute confidence score and publishing status per CONVENTIONS.
    Returns: (confidence_score, Event.Status value)
    """
    required_fields = ["title", "genre", "start_at", "venue_name"]
    all_fields_present = all(candidate.get(field) for field in required_fields)

    high_confidence_origins = {Source.Type.FEED, Source.Type.JSONLD, Source.Type.API}
    is_high_origin = source.type in high_confidence_origins

    low_confidence_origins = {Source.Type.FORM, Source.Type.EMAIL, Source.Type.SOCIAL}
    if source.type in low_confidence_origins:
        return (0.5, Event.Status.REVIEW)

    if is_high_origin and all_fields_present and not dedup_collision:
        return (0.9, Event.Status.PUBLISHED)

    return (0.5, Event.Status.REVIEW)
