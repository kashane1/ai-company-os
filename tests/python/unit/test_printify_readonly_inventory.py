import httpx
import pytest

from packages.pod.runner import DraftError, PrintifyClient
from scripts.home_from_working_printify_snapshot import default_output_path, sanitize_product


def test_iter_products_is_get_only_and_paginates():
    requests = []

    def handler(request):
        requests.append(request)
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(
                200,
                json={"current_page": 1, "last_page": 2, "data": [{"id": "a"}]},
            )
        return httpx.Response(
            200,
            json={"current_page": 2, "last_page": 2, "data": [{"id": "b"}]},
        )

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        assert [product["id"] for product in client.iter_products(limit=50)] == ["a", "b"]
    finally:
        client.close()
    assert [request.method for request in requests] == ["GET", "GET"]
    assert all(request.url.path.endswith("/shops/28779955/products.json") for request in requests)


def test_catalog_shipping_read_uses_get_only_exact_route():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"profiles": []})

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        assert client.get_catalog_shipping(6, 99) == {"profiles": []}
    finally:
        client.close()

    assert [request.method for request in requests] == ["GET"]
    assert requests[0].url.path.endswith(
        "/catalog/blueprints/6/print_providers/99/shipping.json"
    )


def test_catalog_standard_shipping_read_uses_named_v2_route():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": []})

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        assert client.get_catalog_standard_shipping(6, 99) == {"data": []}
    finally:
        client.close()

    assert [request.method for request in requests] == ["GET"]
    assert requests[0].url.path == (
        "/v2/catalog/blueprints/6/print_providers/99/shipping/standard.json"
    )


@pytest.mark.parametrize("blueprint_id,provider_id", [(True, 99), (6, False), (0, 99), (6, 0)])
def test_catalog_shipping_read_rejects_invalid_identifiers(blueprint_id, provider_id):
    client = PrintifyClient("token", transport=httpx.MockTransport(lambda request: None))
    try:
        with pytest.raises(DraftError, match="positive integer"):
            client.get_catalog_shipping(blueprint_id, provider_id)
    finally:
        client.close()


def test_iter_products_rejects_limit_above_current_printify_maximum():
    client = PrintifyClient("token", transport=httpx.MockTransport(lambda request: None))
    try:
        try:
            list(client.iter_products(limit=51))
        except Exception as exc:
            assert "1 through 50" in str(exc)
        else:
            raise AssertionError("Printify's maximum page size must be enforced")
    finally:
        client.close()


def test_iter_products_rejects_invalid_page_shapes():
    def handler(request):
        return httpx.Response(200, json={"current_page": 1, "last_page": 1, "data": {}})

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        try:
            list(client.iter_products())
        except Exception as exc:
            assert "product list" in str(exc).lower()
        else:
            raise AssertionError("invalid product list must fail closed")
    finally:
        client.close()


@pytest.mark.parametrize(
    ("current_page", "last_page"),
    [
        (True, 1),
        (1, True),
        (2, 2),
        (1, 0),
    ],
)
def test_iter_products_rejects_malformed_page_metadata(current_page, last_page):
    def handler(request):
        return httpx.Response(
            200,
            json={"current_page": current_page, "last_page": last_page, "data": []},
        )

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(DraftError, match="product list response is invalid"):
            list(client.iter_products())
    finally:
        client.close()


def test_iter_products_rejects_response_for_wrong_requested_page():
    def handler(request):
        return httpx.Response(
            200,
            json={"current_page": 2, "last_page": 2, "data": [{"id": "wrong-page"}]},
        )

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(DraftError, match="product list response is invalid"):
            list(client.iter_products())
    finally:
        client.close()


def test_iter_products_rejects_changing_last_page_and_never_repeats_a_page():
    requests = []

    def handler(request):
        requests.append(request)
        page = int(request.url.params["page"])
        if page == 1:
            return httpx.Response(
                200,
                json={"current_page": 1, "last_page": 3, "data": [{"id": "a"}]},
            )
        return httpx.Response(
            200,
            json={"current_page": 2, "last_page": 2, "data": [{"id": "b"}]},
        )

    client = PrintifyClient("token", transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(DraftError, match="product list response is invalid"):
            list(client.iter_products())
    finally:
        client.close()
    assert [request.url.params["page"] for request in requests] == ["1", "2"]


def test_snapshot_sanitizer_keeps_relationship_fields_but_compacts_variants():
    product = {
        "id": "product-1",
        "title": "Title",
        "external": {
            "id": "listing-1",
            "handle": "listing",
            "buyer_email": "must-not-survive@example.com",
            "private_metadata": {"token": "must-not-survive"},
        },
        "description": "large buyer-facing copy is not needed",
        "variants": [
            {"id": 1, "sku": "private-detail", "cost": 740, "price": 1799, "is_enabled": True, "is_available": True},
            {"id": 2, "cost": 740, "price": 1799, "is_enabled": True, "is_available": False},
            {"id": 3, "cost": 900, "price": 1999, "is_enabled": False, "is_available": True},
        ],
    }
    sanitized = sanitize_product(product)
    assert sanitized["external"] == {"id": "listing-1", "handle": "listing"}
    assert sanitized["variant_summary"] == {
        "total_count": 3,
        "enabled_count": 2,
        "available_enabled_count": 1,
        "enabled_cost_cents": [740],
        "enabled_price_cents": [1799],
    }
    assert "variants" not in sanitized
    assert "description" not in sanitized
    assert "sku" not in str(sanitized)


def test_default_snapshot_output_uses_observed_runtime_date() -> None:
    assert str(default_output_path("2026-09-17T03:04:05Z")).endswith(
        "evidence/2026-09-17/printify-products.json"
    )


def test_snapshot_output_refuses_to_overwrite_without_explicit_flag(tmp_path):
    from scripts.home_from_working_printify_snapshot import ensure_output_writable

    output = tmp_path / "snapshot.json"
    output.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError, match="--overwrite"):
        ensure_output_writable(output, overwrite=False)
    ensure_output_writable(output, overwrite=True)
