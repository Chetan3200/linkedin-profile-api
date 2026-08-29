import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.linkedin.errors import UpstreamSchemaChanged

REFERENCE_RE = re.compile(r"^\$(?P<tag>[LQ@]?)(?P<chunk>[0-9a-f]+)(?::(?P<path>.*))?$")
INVALID_UNICODE_ESCAPE_RE = re.compile(r"\\u(?![0-9a-fA-F]{4})")


@dataclass(frozen=True)
class FlightImport:
    value: Any


class FlightDocument:
    def __init__(self, frames: dict[int, Any]) -> None:
        self.frames = frames

    @classmethod
    def parse(cls, content: bytes) -> "FlightDocument":
        frames: dict[int, Any] = {}
        try:
            for chunk_id, body, is_text in _flight_frames(content):
                if is_text:
                    frames[chunk_id] = body
                    continue
                if body.startswith("I"):
                    frames[chunk_id] = FlightImport(_json_loads(body[1:]))
                else:
                    frames[chunk_id] = _json_loads(body)
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            raise UpstreamSchemaChanged() from exc
        if not frames:
            raise UpstreamSchemaChanged()
        return cls(frames)

    def resolved_frames(self) -> list[Any]:
        return [
            self.resolve(value)
            for value in self.frames.values()
            if not isinstance(value, FlightImport)
        ]

    def root(self) -> Any:
        if 0 not in self.frames or isinstance(self.frames[0], FlightImport):
            raise UpstreamSchemaChanged()
        return self.resolve(self.frames[0])

    def resolve(self, value: Any, stack: frozenset[int] = frozenset()) -> Any:
        if isinstance(value, list):
            return [self.resolve(item, stack) for item in value]
        if isinstance(value, dict):
            return {key: self.resolve(item, stack) for key, item in value.items()}
        if not isinstance(value, str):
            return value
        if value == "$undefined":
            return None
        if value.startswith("$n") and value[2:].isdigit():
            return int(value[2:])
        if value.startswith("$$"):
            return value[1:]

        match = REFERENCE_RE.fullmatch(value)
        if not match:
            return value
        chunk_id = int(match.group("chunk"), 16)
        if chunk_id in stack or chunk_id not in self.frames:
            return value
        target = self.frames[chunk_id]
        if isinstance(target, FlightImport):
            return value
        resolved = self.resolve(target, stack | {chunk_id})
        path = match.group("path")
        if path:
            for part in path.split(":"):
                resolved = _path_value(resolved, part)
        if match.group("tag") == "Q" and isinstance(resolved, list):
            try:
                return {str(key): item for key, item in resolved}
            except (TypeError, ValueError):
                return resolved
        return resolved

    def objects(self) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        for frame in self.resolved_frames():
            _collect_objects(frame, objects)
        return objects

    def root_objects(self) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        _collect_objects(self.root(), objects)
        return objects

    def pagination_request(
        self, pager_id: str, *, filter_name: str | None = None
    ) -> dict[str, Any] | None:
        for value in self.root_objects():
            if value.get("$type") != "proto.sdui.actions.requests.PaginationRequest":
                continue
            if value.get("pagerId") != pager_id:
                continue
            payload = value.get("requestedArguments", {}).get("payload", {})
            if filter_name is not None and payload.get("filter") != filter_name:
                continue
            return deepcopy(value)

        root = self.root()
        if isinstance(root, list) and len(root) > 1 and isinstance(root[1], str):
            try:
                value = json.loads(root[1])
            except json.JSONDecodeError:
                return None
            if isinstance(value, dict) and value.get("pagerId") == pager_id:
                return value
        return None

    def component_request(self, component_id: str) -> dict[str, Any] | None:
        return next(
            (
                deepcopy(value)
                for value in self.root_objects()
                if value.get("newComponentId") == component_id
                and isinstance(value.get("requestedArguments"), dict)
            ),
            None,
        )


def _path_value(value: Any, part: str) -> Any:
    if part == "props" and _is_element(value):
        return value[3]
    if isinstance(value, dict):
        return value.get(part)
    if isinstance(value, list) and part.isdigit():
        index = int(part)
        return value[index] if index < len(value) else None
    return None


def _is_element(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 4 and value[0] == "$"


def _collect_objects(value: Any, output: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        output.append(value)
        for child in value.values():
            _collect_objects(child, output)
    elif isinstance(value, list):
        for child in value:
            _collect_objects(child, output)


def _json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return json.loads(INVALID_UNICODE_ESCAPE_RE.sub(r"\\\\u", value))


def _flight_frames(content: bytes):
    position = 0
    while position < len(content):
        while position < len(content) and content[position : position + 1] in {b"\n", b"\r"}:
            position += 1
        if position >= len(content):
            break
        colon = content.find(b":", position)
        if colon < 0:
            raise ValueError("Flight frame label is missing")
        chunk_id = int(content[position:colon], 16)
        body_start = colon + 1
        if content[body_start : body_start + 1] == b"T":
            comma = content.find(b",", body_start + 1)
            if comma < 0:
                raise ValueError("Flight text length is missing")
            length = int(content[body_start + 1 : comma], 16)
            text_start = comma + 1
            text_end = text_start + length
            if text_end > len(content):
                raise ValueError("Flight text chunk is truncated")
            yield chunk_id, content[text_start:text_end].decode("utf-8"), True
            position = text_end
            continue

        newline = content.find(b"\n", body_start)
        body_end = newline if newline >= 0 else len(content)
        yield chunk_id, content[body_start:body_end].decode("utf-8"), False
        position = body_end + 1
