import pytest

from app.linkedin import endpoints


def test_top_card_preserves_restli_tuple_punctuation() -> None:
    path = endpoints.top_card("synthetic-member")

    assert "variables=(memberIdentity:synthetic-member)" in path
    assert "%28" not in path
    assert endpoints.GRAPHQL_QUERY_IDS["top_card"] in path


def test_rsc_profile_and_detail_paths_are_fixed() -> None:
    assert endpoints.profile_page("example") == "/in/example/"
    assert endpoints.detail_section("example", "skills") == "/in/example/details/skills/"

    with pytest.raises(ValueError):
        endpoints.detail_section("example", "unsupported")
