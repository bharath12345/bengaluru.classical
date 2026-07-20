import pytest
from django.core.management import call_command

from apps.core.models import City
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_seed_is_idempotent():
    call_command("seed_bengaluru")
    call_command("seed_bengaluru")
    assert City.objects.filter(slug="bengaluru").count() == 1
    assert Source.objects.count() >= 5
