"""Live Google Lens search through SerpApi."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from faceproof.domain import SearchCandidate, SearchTrace
from faceproof.errors import ConfigurationError, SearchError


@dataclass(frozen=True)
class LensSearchResult:
    trace: SearchTrace
    candidates: tuple[SearchCandidate, ...]


class SerpApiLensClient:
    upload_url = "https://serpapi.com/image"
    search_url = "https://serpapi.com/search.json"

    def __init__(
        self,
        api_key: str,
        social_domains: tuple[str, ...],
        *,
        timeout_seconds: float = 45.0,
    ) -> None:
        if not api_key.strip():
            raise ConfigurationError(
                "The live search key is missing.",
                "Add SERPAPI_API_KEY to .context/secrets.env and restart FaceProof.",
            )
        self.api_key = api_key
        self.social_domains = social_domains
        self.timeout_seconds = timeout_seconds

    async def search(self, image_bytes: bytes, *, query_kind: str) -> LensSearchResult:
        headers = {"User-Agent": "FaceProof/0.1"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
                upload = await client.post(
                    self.upload_url,
                    data={"api_key": self.api_key},
                    files={"image": (f"{query_kind}.jpg", image_bytes, "image/jpeg")},
                )
                upload.raise_for_status()
                upload_data = upload.json()
                if error := upload_data.get("error"):
                    raise SearchError(
                        f"SerpApi rejected the {query_kind} image: {error}",
                        "Check the image format and the remaining SerpApi search allowance.",
                    )
                image_id = upload_data.get("image_id")
                if not image_id:
                    raise SearchError("SerpApi did not return an image identifier.")

                response = await client.get(
                    self.search_url,
                    params={
                        "engine": "google_lens",
                        "image_id": image_id,
                        "api_key": self.api_key,
                        "no_cache": "true",
                        "safe": "active",
                        "hl": "en",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except SearchError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise SearchError(
                "The live visual search could not be completed.",
                "Check the network and SerpApi key, then retry the same image.",
            ) from exc

        if error := payload.get("error"):
            raise SearchError(
                f"Google Lens search failed: {error}",
                "Check the SerpApi account status and retry.",
            )

        metadata = payload.get("search_metadata") or {}
        raw_results = self._collect_results(payload)
        candidates: list[SearchCandidate] = []
        seen: set[str] = set()
        for index, result in enumerate(raw_results, start=1):
            link = str(result.get("link") or "").strip()
            if not link or link in seen or not self._is_social_url(link):
                continue
            seen.add(link)
            candidates.append(
                SearchCandidate(
                    candidate_id=f"{query_kind}-{len(candidates) + 1}",
                    position=self._position(result.get("position"), index),
                    title=str(result.get("title") or "Untitled social result").strip(),
                    source=str(result.get("source") or urlparse(link).hostname or "Social web"),
                    post_url=link,
                    media_url=self._clean_optional(result.get("image")),
                    thumbnail_url=self._clean_optional(result.get("thumbnail")),
                    exact_match=bool(result.get("exact_matches") or result.get("is_exact_match")),
                    query_kind=query_kind,
                )
            )

        trace = SearchTrace(
            query_kind=query_kind,
            search_id=self._clean_optional(metadata.get("id")),
            provider_status=str(metadata.get("status") or "Unknown"),
            created_at=self._clean_optional(metadata.get("created_at")),
            result_count=len(raw_results),
            social_result_count=len(candidates),
        )
        return LensSearchResult(trace=trace, candidates=tuple(candidates))

    def _is_social_url(self, value: str) -> bool:
        try:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"}:
                return False
            hostname = (parsed.hostname or "").lower().removeprefix("www.")
        except ValueError:
            return False
        return any(
            hostname == domain or hostname.endswith(f".{domain}") for domain in self.social_domains
        )

    @staticmethod
    def _collect_results(payload: dict[str, object]) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for key in ("exact_matches", "visual_matches", "organic_results", "short_videos"):
            items = payload.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        normalized = dict(item)
                        if key == "exact_matches":
                            normalized["is_exact_match"] = True
                        results.append(normalized)
        return results

    @staticmethod
    def _clean_optional(value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _position(value: object, fallback: int) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return fallback
