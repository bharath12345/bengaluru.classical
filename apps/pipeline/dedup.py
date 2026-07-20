import re
from difflib import SequenceMatcher

from django.utils.text import slugify

from apps.core.models import Artist, Venue
from apps.events.models import Event

FUZZY_THRESHOLD = 0.85


def compute_dedup_key(date: str, venue_name: str, artist_names: list[str]) -> str:
    date_part = re.sub(r"[^\d]", "", date)[:8]
    venue_part = slugify(venue_name)
    artist_part = "_".join(sorted(slugify(name) for name in artist_names))
    return f"{date_part}|{venue_part}|{artist_part}"


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_or_create_venue(name: str, city) -> Venue:
    venues = Venue.objects.filter(city=city)
    for venue in venues:
        if fuzzy_ratio(venue.name, name) >= FUZZY_THRESHOLD:
            return venue

    slug = slugify(name) or "venue"
    base_slug = slug
    counter = 1
    while Venue.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return Venue.objects.create(name=name, slug=slug, city=city)


def find_or_create_artist(name: str) -> Artist:
    artists = Artist.objects.all()
    for artist in artists:
        if fuzzy_ratio(artist.name, name) >= FUZZY_THRESHOLD:
            return artist
        for alt in artist.alt_names or []:
            if fuzzy_ratio(alt, name) >= FUZZY_THRESHOLD:
                return artist

    slug = slugify(name) or "artist"
    base_slug = slug
    counter = 1
    while Artist.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return Artist.objects.create(name=name, slug=slug)


def find_duplicate_event(dedup_key: str) -> Event | None:
    try:
        return Event.objects.get(dedup_key=dedup_key)
    except Event.DoesNotExist:
        return None
