from pathlib import Path

import pytest

from app.linkedin.errors import UpstreamSchemaChanged
from app.linkedin.rsc import FlightDocument


def test_parses_and_resolves_flight_frames() -> None:
    content = (Path(__file__).parent / "fixtures" / "flight_stream.rsc").read_bytes()

    document = FlightDocument.parse(content)
    objects = document.objects()

    assert any(value.get("children") == "Synthetic text" for value in objects)
    assert any(value.get("count") == 3 for value in objects)
    assert any(
        value.get("states", {}).get("category", {}).get("children") == "Synthetic item"
        for value in objects
    )


def test_rejects_invalid_flight_stream() -> None:
    with pytest.raises(UpstreamSchemaChanged):
        FlightDocument.parse(b"not-a-flight-frame")


def test_tolerates_invalid_unicode_escape_in_rendered_text() -> None:
    document = FlightDocument.parse(b'0:{"children":"Synthetic \\user text"}')

    assert document.root()["children"] == "Synthetic \\user text"
