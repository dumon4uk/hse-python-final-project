import os
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(autouse=True)
def _ensure_env_for_tests(monkeypatch: pytest.MonkeyPatch):
    if not os.getenv("BOT_TOKEN"):
        monkeypatch.setenv("BOT_TOKEN", "TEST_BOT_TOKEN")


@pytest.fixture
def fake_info():
    return {
        "id": "abc123",
        "duration": 120,
        "formats": [],
    }
