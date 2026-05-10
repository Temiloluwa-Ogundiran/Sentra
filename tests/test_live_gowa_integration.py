import os

import pytest

from app.integrations.gowa import GowaClient


@pytest.mark.skipif(
    not os.getenv("GOWA_BASE_URL"),
    reason="Live GOWA base URL not configured",
)
@pytest.mark.asyncio
async def test_live_gowa_health_contract():
    client = GowaClient()
    assert client.base_url
