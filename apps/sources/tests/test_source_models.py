import pytest
from django.utils import timezone

from apps.sources.factories import SourceFactory
from apps.sources.models import Source

pytestmark = pytest.mark.django_db


def test_source_defaults():
    source = SourceFactory()
    assert source.active is True
    assert source.seasonal is False
    assert source.health_status == Source.Health.UNKNOWN
    assert source.last_seen_at is None


def test_source_type_choices():
    source = SourceFactory(type=Source.Type.FEED)
    assert source.type == "feed"


def test_mark_seen_sets_ok_and_timestamp():
    source = SourceFactory()
    now = timezone.now()
    source.mark_seen(now)
    source.refresh_from_db()
    assert source.health_status == Source.Health.OK
    assert source.last_seen_at == now


def test_source_str_includes_name():
    source = SourceFactory(name="Nadasurabhi")
    assert "Nadasurabhi" in str(source)
