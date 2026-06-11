from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest

from packages.prospecting.web_presence import (
    BraveSearchVerifier,
    DataForSEOSearchVerifier,
    SearchResult,
    classify_web_presence,
    verify_record_web_presence,
)
from packages.schemas.prospect import ProspectRecord, WebVerifyVerdict

FIXED = datetime(2026, 6, 10, tzinfo=timezone.utc)


def _record() -> ProspectRecord:
    return ProspectRecord(
        place_id="places/abc123",
        display_name="Tonic Salon",
        formatted_address="1420 Pine St, Seattle, WA 98101",
        phone="+1 206-555-0100",
        types=["beauty_salon"],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        user_ratings_total=42,
        composite_cohort="A_gold",
        priority_score=42,
    )


def _record_named(name: str) -> ProspectRecord:
    base = _record().to_dict()
    base["display_name"] = name
    return ProspectRecord.from_dict(base)


def test_prospect_record_round_trips_web_verify_fields() -> None:
    record = ProspectRecord.from_dict(
        {
            **_record().to_dict(),
            "web_verify_class": "web_search",
            "web_verify_verdict": "marketplace_only",
            "web_verify_url": "https://www.yelp.com/biz/tonic-salon-seattle",
            "web_verify_confidence": 0.78,
            "web_verify_note": "directory and review profiles found; no owned site",
            "web_verified_at": FIXED.isoformat(),
            "web_verify_method": "brave",
        }
    )

    assert record.web_verify_verdict is WebVerifyVerdict.MARKETPLACE_ONLY
    assert ProspectRecord.from_dict(record.to_dict()) == record


@pytest.mark.parametrize(
    ("results", "expected", "url"),
    [
        (
            [
                SearchResult(
                    title="Tonic Salon | Seattle hair care",
                    url="https://tonicsalonseattle.com/",
                    description="Haircuts and color in Seattle.",
                )
            ],
            WebVerifyVerdict.OWNED_SITE,
            "https://tonicsalonseattle.com/",
        ),
        (
            [
                SearchResult(
                    title="Reunion Bakery reopens in bigger space",
                    url="https://www.denvergazette.com/2026/05/05/denvers-reunion-bakery",
                    description="News story about a local bakery.",
                )
            ],
            WebVerifyVerdict.AMBIGUOUS,
            "https://www.denvergazette.com/2026/05/05/denvers-reunion-bakery",
        ),
        (
            [
                SearchResult(
                    title="Tonic Salon on ClassPass",
                    url="https://classpass.com/studios/tonic-salon-seattle",
                    description="Book fitness and wellness appointments.",
                )
            ],
            WebVerifyVerdict.MARKETPLACE_ONLY,
            "https://classpass.com/studios/tonic-salon-seattle",
        ),
        (
            [
                SearchResult(
                    title="Tonic Salon on Instagram",
                    url="https://www.instagram.com/tonicsalon/",
                    description="Photos and videos.",
                )
            ],
            WebVerifyVerdict.SOCIAL_ONLY,
            "https://www.instagram.com/tonicsalon/",
        ),
        (
            [
                SearchResult(
                    title="Tonic Salon - Yelp",
                    url="https://www.yelp.com/biz/tonic-salon-seattle",
                    description="Reviews, phone, and directions.",
                )
            ],
            WebVerifyVerdict.MARKETPLACE_ONLY,
            "https://www.yelp.com/biz/tonic-salon-seattle",
        ),
        ([], WebVerifyVerdict.NONE_FOUND, ""),
        (
            [
                SearchResult(
                    title="Seattle salon roundup",
                    url="https://localpaper.example/best-salons",
                    description="A list of salons near downtown.",
                )
            ],
            WebVerifyVerdict.AMBIGUOUS,
            "https://localpaper.example/best-salons",
        ),
    ],
)
def test_classify_web_presence_is_conservative(
    results: list[SearchResult], expected: WebVerifyVerdict, url: str
) -> None:
    verdict = classify_web_presence(_record(), results)

    assert verdict.verdict is expected
    assert verdict.url == url
    assert 0 <= verdict.confidence <= 1


def test_verify_record_web_presence_writes_verdict_fields() -> None:
    class StubVerifier:
        method = "stub-search"

        def search(self, query: str) -> list[SearchResult]:
            assert "Tonic Salon" in query
            assert "Seattle" in query
            return [
                SearchResult(
                    title="Tonic Salon - Yelp",
                    url="https://www.yelp.com/biz/tonic-salon-seattle",
                    description="Reviews and directions.",
                )
            ]

    updated = verify_record_web_presence(_record(), StubVerifier(), now=lambda: FIXED)

    assert updated.web_verify_class == "web_search"
    assert updated.web_verify_verdict is WebVerifyVerdict.MARKETPLACE_ONLY
    assert updated.web_verify_method == "stub-search"
    assert updated.web_verified_at == FIXED.isoformat()
    assert updated.web_verify_url == "https://www.yelp.com/biz/tonic-salon-seattle"


def test_news_article_about_business_is_ambiguous_not_owned() -> None:
    verdict = classify_web_presence(
        _record_named("Reunion Bakery"),
        [
            SearchResult(
                title="Reunion Bakery reopens in bigger space",
                url="https://www.denvergazette.com/2026/05/05/denvers-reunion-bakery",
                description="News story about a local bakery.",
            )
        ],
    )

    assert verdict.verdict is WebVerifyVerdict.AMBIGUOUS


def test_brave_search_verifier_sends_subscription_token_and_parses_web_results() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/res/v1/web/search"
        assert request.headers["X-Subscription-Token"] == "brave_key"
        assert request.url.params["q"] == "Tonic Salon Seattle"
        assert request.url.params["result_filter"] == "web"
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Tonic Salon",
                            "url": "https://tonicsalonseattle.com/",
                            "description": "Haircuts and color.",
                        }
                    ]
                }
            },
            request=request,
        )

    verifier = BraveSearchVerifier(
        api_key="brave_key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert verifier.search("Tonic Salon Seattle") == [
        SearchResult(
            title="Tonic Salon",
            url="https://tonicsalonseattle.com/",
            description="Haircuts and color.",
        )
    ]
    assert len(requests) == 1


def test_dataforseo_search_verifier_posts_task_and_reads_regular_results() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Authorization"].startswith("Basic ")
        if request.url.path.endswith("/v3/serp/google/organic/task_post"):
            body = json.loads(request.content.decode())
            assert body == [
                {
                    "keyword": "Tonic Salon Seattle",
                    "language_code": "en",
                    "location_code": 2840,
                    "device": "desktop",
                    "os": "windows",
                    "depth": 10,
                }
            ]
            return httpx.Response(
                200,
                json={
                    "tasks": [
                        {
                            "id": "task_123",
                            "status_code": 20100,
                            "status_message": "Task Created.",
                        }
                    ]
                },
                request=request,
            )
        assert request.url.path.endswith("/v3/serp/google/organic/task_get/regular/task_123")
        return httpx.Response(
            200,
            json={
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "type": "organic",
                                        "title": "Tonic Salon",
                                        "url": "https://tonicsalonseattle.com/",
                                        "description": "Haircuts and color.",
                                    },
                                    {
                                        "type": "paid",
                                        "title": "Ad",
                                        "url": "https://ads.example/",
                                    },
                                ]
                            }
                        ],
                    }
                ]
            },
            request=request,
        )

    verifier = DataForSEOSearchVerifier(
        login="dfs_login",
        password="dfs_password",
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://api.dataforseo.com",
        ),
        poll_interval_seconds=0,
        max_polls=1,
    )

    assert verifier.search("Tonic Salon Seattle") == [
        SearchResult(
            title="Tonic Salon",
            url="https://tonicsalonseattle.com/",
            description="Haircuts and color.",
        )
    ]
    assert len(requests) == 2
