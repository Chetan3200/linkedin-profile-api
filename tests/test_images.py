from app.linkedin.images import resolve_vector_image


def test_selects_largest_vector_image_artifact() -> None:
    value = {
        "vectorImage": {
            "rootUrl": "https://media.example.invalid/",
            "artifacts": [
                {"width": 400, "height": 400, "fileIdentifyingUrlPathSegment": "a.jpg"},
                {"width": 1200, "height": 300, "fileIdentifyingUrlPathSegment": "b.jpg"},
                {"width": 800, "height": 800, "fileIdentifyingUrlPathSegment": "c.jpg"},
            ],
        }
    }

    image = resolve_vector_image(value)

    assert image is not None
    assert image.url == "https://media.example.invalid/c.jpg"
    assert (image.width, image.height) == (800, 800)


def test_invalid_vector_image_returns_none() -> None:
    assert resolve_vector_image({"rootUrl": "https://example.invalid/"}) is None
