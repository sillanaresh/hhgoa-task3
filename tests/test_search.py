from __future__ import annotations

import httpx
import pytest
import respx

from faceproof.search import SerpApiLensClient


@pytest.mark.asyncio
@respx.mock
async def test_live_search_uploads_image_and_filters_social_results() -> None:
    upload = respx.post("https://serpapi.com/image").mock(
        return_value=httpx.Response(200, json={"image_id": "fresh-image-id"})
    )
    search = respx.get("https://serpapi.com/search.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "search_metadata": {"id": "search-id", "status": "Success"},
                "exact_matches": [
                    {
                        "position": "not-an-integer",
                        "title": "Matching public post",
                        "source": "Instagram",
                        "link": "https://www.instagram.com/p/real-result/",
                        "image": "https://images.example.test/match.jpg",
                    }
                ],
                "visual_matches": [
                    {
                        "position": 2,
                        "title": "Non social result",
                        "link": "https://example.com/article",
                    },
                    {
                        "position": 3,
                        "title": "Second social result",
                        "link": "https://x.com/example/status/123",
                        "thumbnail": "https://images.example.test/thumb.jpg",
                    },
                ],
            },
        )
    )
    client = SerpApiLensClient("test-key", ("instagram.com", "x.com"))

    result = await client.search(b"jpeg", query_kind="face_crop")

    assert upload.called
    assert search.called
    assert search.calls[0].request.url.params["engine"] == "google_lens"
    assert search.calls[0].request.url.params["no_cache"] == "true"
    assert [item.post_url for item in result.candidates] == [
        "https://www.instagram.com/p/real-result/",
        "https://x.com/example/status/123",
    ]
    assert result.candidates[0].exact_match is True
    assert result.candidates[0].position == 1
    assert result.trace.social_result_count == 2


def test_social_filter_rejects_lookalike_and_non_http_urls() -> None:
    client = SerpApiLensClient("test-key", ("instagram.com",))

    assert client._is_social_url("https://www.instagram.com/p/valid/") is True
    assert client._is_social_url("https://instagram.com.attacker.test/p/nope") is False
    assert client._is_social_url("javascript://instagram.com/p/nope") is False
