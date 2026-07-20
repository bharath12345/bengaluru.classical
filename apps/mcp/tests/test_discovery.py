import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_well_known_mcp_json(client: Client):
    response = client.get("/.well-known/mcp.json")
    assert response.status_code == 200
    body = b"".join(response.streaming_content)
    assert b"search_events" in body
