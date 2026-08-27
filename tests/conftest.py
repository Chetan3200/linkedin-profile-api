import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def complete_payload() -> dict[str, Any]:
    fixture_path = Path(__file__).parent / "fixtures" / "profile_complete.json"
    return json.loads(fixture_path.read_text())
