from django.core.management.base import BaseCommand

from apps.core.models import City
from apps.sources.models import Source

STARTER_SOURCES = [
    # (name, type, url)
    (
        "Bangalore International Centre",
        Source.Type.FEED,
        "https://bangaloreinternationalcentre.org/events/?ical=1",
    ),
    (
        "Indian Music Experience",
        Source.Type.JSONLD,
        "https://www.indianmusicexperience.org/events/",
    ),
    ("SPIC MACAY Karnataka", Source.Type.API, "https://api.spicmacay.org/graphql"),
    ("Sri Rama Lalitha Kala Mandira", Source.Type.HTML, "https://srlkmandira.org/events/"),
    ("Nadasurabhi", Source.Type.HTML, "https://nadasurabhi.org/jobs"),
    ("Sree Ramaseva Mandali (Chamarajpet)", Source.Type.HTML, "https://ramanavami.org/schedule"),
    ("Seshadripuram Ramaseva Samithi", Source.Type.HTML, "https://ssrss.org/schedule"),
    ("Bharatiya Vidya Bhavan Bengaluru", Source.Type.HTML, "https://bhavankarnataka.com/allevents"),
    ("Sangamam India", Source.Type.HTML, "https://sangamamindia.org/"),
    ("Public submission form", Source.Type.FORM, ""),
    ("Forwarded email", Source.Type.EMAIL, ""),
]


class Command(BaseCommand):
    help = "Idempotently seed the Bengaluru city and starter source registry."

    def handle(self, *args, **options):
        city, created = City.objects.get_or_create(slug="bengaluru", defaults={"name": "Bengaluru"})
        self.stdout.write(f"City: {'created' if created else 'exists'} -> {city}")

        for name, type_, url in STARTER_SOURCES:
            city_fk = None if type_ in (Source.Type.EMAIL, Source.Type.FORM) else city
            _, made = Source.objects.get_or_create(
                name=name, defaults={"type": type_, "url": url, "city": city_fk}
            )
            self.stdout.write(f"Source: {'created' if made else 'exists'} -> {name}")
