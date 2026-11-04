"""Prepare, update, and verify one operated native Printify duplicate."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image

from packages.pod.template import (
    DraftError,
    artwork_placement,
    assert_native_copy,
    make_print_areas,
    mockup_signature,
    verify_update,
)
from packages.policies.pod import require_draft_approval
from packages.schemas.approval import ApprovalRecord, ApprovalStatus

SHOP_ID = 28779955
TEMPLATE_ID = "6a9860cc0bf15ba9490bfe3a"
PATCH_FIELDS = {"title", "description", "tags", "print_areas"}
API_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
BROWSER_UPLOAD_MAX_BYTES = 100 * 1024 * 1024


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def run_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DraftError("This draft run is already in progress.") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def snapshot_digest(product) -> str:
    def stable(value):
        if isinstance(value, dict):
            return {k: stable(v) for k, v in value.items() if k not in {"imageId", "updated_at"}}
        if isinstance(value, list):
            return [stable(v) for v in value]
        return value
    return digest(stable(product))


def require_unpublished(product) -> None:
    if not isinstance(product, dict):
        raise DraftError("Product response is missing or invalid.")
    external = product.get("external")
    if external is None:
        external = {}
    if not isinstance(external, dict):
        raise DraftError("Product publication metadata is invalid.")
    if external.get("id") or external.get("handle"):
        raise DraftError("Linked/published products cannot be changed by the draft runner.")
    if product.get("is_locked") is not False or product.get("is_deleted") is not False:
        raise DraftError("Draft must be confirmed unlocked and not deleted.")


class PrintifyClient:
    """Fixed public API surface; no create, duplicate, publish, or delete methods."""

    def __init__(self, token: str, *, transport=None):
        self.http = httpx.Client(
            base_url="https://api.printify.com/v1/",
            headers={"Authorization": "Bearer " + token,
                     "User-Agent": "HomeFromWorking-DraftRunner", "Accept": "application/json"},
            timeout=45,
            follow_redirects=False,
            transport=transport,
        )

    def close(self):
        self.http.close()

    def _product_path(self, identifier: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{24}", identifier):
            raise DraftError("Product ID must be the exact 24-character Printify ID.")
        return f"shops/{SHOP_ID}/products/{identifier}.json"

    def _request(self, method, path, payload=None):
        try:
            response = self.http.request(method, path, json=payload)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as exc:
            raise DraftError(f"Printify returned HTTP {exc.response.status_code}; inspect the run.") from None
        except (httpx.RequestError, ValueError):
            raise DraftError("Printify response was uncertain; reconcile saved state before retrying.") from None

    def get_product(self, identifier):
        return self._request("GET", self._product_path(identifier))

    def get_catalog_shipping(self, blueprint_id: int, print_provider_id: int):
        """Read current standard shipping rates for an exact catalog pairing."""
        self._validate_catalog_ids(blueprint_id, print_provider_id)
        return self._request(
            "GET",
            f"catalog/blueprints/{blueprint_id}/print_providers/"
            f"{print_provider_id}/shipping.json",
        )

    def get_catalog_standard_shipping(
        self, blueprint_id: int, print_provider_id: int
    ):
        """Read V2 rates from the explicitly named standard-shipping route."""
        self._validate_catalog_ids(blueprint_id, print_provider_id)
        return self._request(
            "GET",
            "https://api.printify.com/v2/catalog/blueprints/"
            f"{blueprint_id}/print_providers/{print_provider_id}/"
            "shipping/standard.json",
        )

    @staticmethod
    def _validate_catalog_ids(blueprint_id: int, print_provider_id: int) -> None:
        for value in (blueprint_id, print_provider_id):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise DraftError(
                    "Blueprint and print provider IDs must be positive integers."
                )

    def iter_products(self, *, limit=50):
        """Yield every shop product through Printify's read-only paginated route."""
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            raise DraftError("Printify product list limit must be 1 through 50.")
        page = 1
        expected_last_page = None
        while True:
            payload = self._request(
                "GET", f"shops/{SHOP_ID}/products.json?limit={limit}&page={page}"
            )
            products = payload.get("data") if isinstance(payload, dict) else None
            current_page = payload.get("current_page") if isinstance(payload, dict) else None
            last_page = payload.get("last_page") if isinstance(payload, dict) else None
            if (
                not isinstance(products, list)
                or isinstance(current_page, bool)
                or not isinstance(current_page, int)
                or isinstance(last_page, bool)
                or not isinstance(last_page, int)
                or current_page != page
                or last_page < current_page
                or last_page < page
                or (expected_last_page is not None and last_page != expected_last_page)
            ):
                raise DraftError("Printify product list response is invalid.")
            if expected_last_page is None:
                expected_last_page = last_page
            for product in products:
                if not isinstance(product, dict):
                    raise DraftError("Printify product list contains an invalid product.")
                yield product
            if current_page >= last_page:
                return
            page = current_page + 1

    def upload(self, name, content):
        if len(content) > API_UPLOAD_MAX_BYTES:
            raise DraftError("PNG exceeds the runner's 5 MiB upload limit; use a reviewed upload path.")
        return self._request("POST", "uploads/images.json", {
            "file_name": name, "contents": base64.b64encode(content).decode(),
        })

    def update_draft(self, identifier, payload):
        if not payload or not set(payload) <= PATCH_FIELDS:
            raise DraftError("Only artwork, title, description, and tags can be updated.")
        require_unpublished(self.get_product(identifier))
        return self._request("PUT", self._product_path(identifier), payload)


def prepare_run(client, template_id, draft_id, artwork, copy, directory, *, scale_percent=None):
    directory, artwork = Path(directory), Path(artwork).resolve()
    with run_lock(directory):
        if (directory / "review.json").exists():
            raise DraftError("Review already exists; resume it or use a new revision directory.")
        if set(copy) != {"title", "intro", "tags"}:
            raise DraftError("Copy input must contain title, intro, and tags only.")
        if not isinstance(copy["title"], str) or not 1 <= len(copy["title"].strip()) <= 140:
            raise DraftError("Title must contain 1–140 characters.")
        if not isinstance(copy["intro"], str) or not 1 <= len(copy["intro"].strip()) <= 5000:
            raise DraftError("Supply a short design-specific introduction.")
        tags = copy["tags"]
        if (not isinstance(tags, list) or not 1 <= len(tags) <= 13
                or any(not isinstance(t, str) or not 1 <= len(t) <= 20 for t in tags)
                or len(set(tags)) != len(tags)):
            raise DraftError("Use up to 13 unique tags, each 1–20 characters.")
        content = artwork.read_bytes()
        if len(content) > API_UPLOAD_MAX_BYTES:
            raise DraftError("PNG exceeds the runner's 5 MiB upload limit.")
        with Image.open(artwork) as image:
            if image.format != "PNG":
                raise DraftError("Artwork must be a PNG.")
            image.load()
            width, height = image.size
            alpha = image.convert("RGBA").getchannel("A").getextrema()
        if alpha[1] == 0:
            raise DraftError("Artwork is fully transparent; supply visible artwork.")
        placement = artwork_placement(width, height, scale_percent)
        template = client.get_product(template_id)
        before = client.get_product(draft_id)
        assert_native_copy(template, before, SHOP_ID)
        if "\n\nPRODUCT FEATURES" not in template["description"]:
            raise DraftError("Template has no stable PRODUCT FEATURES section; review its copy.")
        description = (copy["intro"].strip() + "\n\nPRODUCT FEATURES"
                       + template["description"].split("\n\nPRODUCT FEATURES", 1)[1])
        upload = {"id": "PENDING_UPLOAD", "width": width, "height": height,
                  "mime_type": "image/png"}
        payload = {"title": copy["title"].strip(), "description": description, "tags": tags,
                   "print_areas": make_print_areas(before, upload, width, height,
                                                    scale_percent=scale_percent)}
        review = {
            "schema_version": 1, "shop_id": SHOP_ID, "template_id": template_id,
            "draft_id": draft_id, "before_fingerprint": snapshot_digest(before),
            "artwork": {"path": str(artwork), "sha256": hashlib.sha256(content).hexdigest(),
                        "width": width, "height": height, "dpi": placement["dpi"],
                        "alpha_range": list(alpha)},
            "payload": payload,
        }
        if scale_percent is not None:
            review["placement"] = placement
        review["revision"] = digest(review)
        save_json(directory / "template.json", template)
        save_json(directory / "before.json", before)
        save_json(directory / "review.json", review)
        approval = ApprovalRecord(
            id=str(uuid4()), status=ApprovalStatus.PENDING,
            summary=f"Update unpublished Printify draft {draft_id}: {payload['title']}",
            created_at=datetime.now(timezone.utc).isoformat(), approval_type="pod_draft_update",
            review_artifact_path=str((directory / "review.json").resolve()),
            subject_type="pod_manifest", subject_id=review["revision"],
            action="update_printify_draft",
        )
        save_json(directory / "approval-request.json", approval.to_dict())
        return review


def prepare_copy_run(client, template_id, draft_id, artwork, copy, directory, *, scale_percent=None):
    """Prepare metadata for artwork already placed through Printify's editor."""
    directory, artwork = Path(directory), Path(artwork).resolve()
    with run_lock(directory):
        if (directory / "review.json").exists():
            raise DraftError("Review already exists; resume it or use a new revision directory.")
        if set(copy) != {"title", "intro", "tags"}:
            raise DraftError("Copy input must contain title, intro, and tags only.")
        if not isinstance(copy["title"], str) or not 1 <= len(copy["title"].strip()) <= 140:
            raise DraftError("Title must contain 1–140 characters.")
        if not isinstance(copy["intro"], str) or not 1 <= len(copy["intro"].strip()) <= 5000:
            raise DraftError("Supply a short design-specific introduction.")
        tags = copy["tags"]
        if (not isinstance(tags, list) or not 1 <= len(tags) <= 13
                or any(not isinstance(t, str) or not 1 <= len(t) <= 20 for t in tags)
                or len(set(tags)) != len(tags)):
            raise DraftError("Use up to 13 unique tags, each 1–20 characters.")
        if artwork.stat().st_size > BROWSER_UPLOAD_MAX_BYTES:
            raise DraftError("PNG exceeds the browser workflow's 100 MiB limit.")
        content = artwork.read_bytes()
        with Image.open(artwork) as image:
            if image.format != "PNG":
                raise DraftError("Artwork must be a PNG.")
            image.load()
            width, height = image.size
            alpha = image.convert("RGBA").getchannel("A").getextrema()
        if alpha[1] == 0:
            raise DraftError("Artwork is fully transparent; supply visible artwork.")
        placement = artwork_placement(width, height, scale_percent)
        template = client.get_product(template_id)
        before = client.get_product(draft_id)
        assert_native_copy(template, before, SHOP_ID)
        front_images = [
            image
            for area in before.get("print_areas", [])
            for placeholder in area.get("placeholders", [])
            if placeholder.get("position") == "front"
            for image in placeholder.get("images", [])
        ]
        if len(front_images) != 1:
            raise DraftError("Browser-edited draft must have exactly one front image.")
        front = front_images[0]
        if (front.get("name") != artwork.name or front.get("width") != width
                or front.get("height") != height or front.get("angle") != 0
                or abs(front.get("x", -1) - placement["x"]) > 0.001
                or abs(front.get("y", -1) - placement["y"]) > 0.001
                or abs(front.get("scale", -1) - placement["scale"]) > 0.001):
            raise DraftError("Browser artwork or placement does not match the reviewed file.")
        if "\n\nPRODUCT FEATURES" not in template["description"]:
            raise DraftError("Template has no stable PRODUCT FEATURES section; review its copy.")
        description = (copy["intro"].strip() + "\n\nPRODUCT FEATURES"
                       + template["description"].split("\n\nPRODUCT FEATURES", 1)[1])
        payload = {"title": copy["title"].strip(), "description": description, "tags": tags}
        review = {
            "schema_version": 1, "shop_id": SHOP_ID, "template_id": template_id,
            "draft_id": draft_id, "before_fingerprint": snapshot_digest(before),
            "artwork": {"path": str(artwork), "sha256": hashlib.sha256(content).hexdigest(),
                        "width": width, "height": height, "dpi": placement["dpi"],
                        "alpha_range": list(alpha)},
            "placement": placement,
            "payload": payload,
        }
        review["revision"] = digest(review)
        save_json(directory / "template.json", template)
        save_json(directory / "before.json", before)
        save_json(directory / "review.json", review)
        approval = ApprovalRecord(
            id=str(uuid4()), status=ApprovalStatus.PENDING,
            summary=f"Update unpublished Printify draft {draft_id}: {payload['title']}",
            created_at=datetime.now(timezone.utc).isoformat(), approval_type="pod_draft_update",
            review_artifact_path=str((directory / "review.json").resolve()),
            subject_type="pod_manifest", subject_id=review["revision"],
            action="update_printify_draft",
        )
        save_json(directory / "approval-request.json", approval.to_dict())
        return review


def apply_run(client, directory, approval):
    directory = Path(directory)
    with run_lock(directory):
        review = read_json(directory / "review.json")
        revision = review["revision"]
        if digest({k: v for k, v in review.items() if k != "revision"}) != revision:
            raise DraftError("Review changed; prepare a new approved revision.")
        require_draft_approval(approval, revision)
        content = Path(review["artwork"]["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != review["artwork"]["sha256"]:
            raise DraftError("Artwork changed; prepare a new approved revision.")
        before = read_json(directory / "before.json")
        if snapshot_digest(before) != review["before_fingerprint"]:
            raise DraftError("Baseline changed; prepare a new approved revision.")
        current = client.get_product(review["draft_id"])
        require_unpublished(current)
        payload = json.loads(json.dumps(review["payload"]))
        scale_percent = review.get("placement", {}).get("requested_scale_percent")
        cached_upload = directory / "upload.json"
        upload = read_json(cached_upload) if cached_upload.exists() else None
        already_verified = False
        if upload:
            if upload.get("asset_sha256") != review["artwork"]["sha256"]:
                raise DraftError("Upload receipt belongs to different artwork.")
            payload["print_areas"] = make_print_areas(
                before, upload, review["artwork"]["width"], review["artwork"]["height"],
                scale_percent=scale_percent,
            )
            try:
                verify_update(before, current, payload)
                already_verified = True
            except DraftError:
                pass
        if not already_verified:
            if snapshot_digest(current) != review["before_fingerprint"]:
                raise DraftError("Draft changed since review; inspect before preparing a new revision.")
            if not upload:
                attempted = directory / "upload-attempted.json"
                if attempted.exists():
                    raise DraftError("Reconcile the uncertain upload before retrying; do not upload again.")
                save_json(attempted, {"revision": revision, "asset_sha256": review["artwork"]["sha256"]})
                upload = client.upload(Path(review["artwork"]["path"]).name, content)
                upload["asset_sha256"] = review["artwork"]["sha256"]
                save_json(cached_upload, upload)
                payload["print_areas"] = make_print_areas(
                    before, upload, review["artwork"]["width"], review["artwork"]["height"],
                    scale_percent=scale_percent,
                )
            save_json(directory / "update-request.json", payload)
            client.update_draft(review["draft_id"], payload)
            current = client.get_product(review["draft_id"])
            save_json(directory / "after.json", current)
            verify_update(before, current, payload)
        receipt = {
            "status": "already_verified" if already_verified else "verified",
            "product_id": current["id"], "revision": revision, "approval_id": approval.id,
            "url": "https://printify.com/app/product-details/" + current["id"],
            "selected_mockups": len(mockup_signature(current)),
            "enabled_variants": sum(v["is_enabled"] for v in current["variants"]),
            "dpi": review["artwork"]["dpi"], "published": False,
        }
        save_json(directory / "receipt.json", receipt)
        return receipt


def apply_copy_run(client, directory, approval):
    """Apply approved title, description, and tags after a reviewed browser artwork edit."""
    directory = Path(directory)
    with run_lock(directory):
        review = read_json(directory / "review.json")
        revision = review["revision"]
        if digest({k: v for k, v in review.items() if k != "revision"}) != revision:
            raise DraftError("Review changed; prepare a new approved revision.")
        require_draft_approval(approval, revision)
        content = Path(review["artwork"]["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != review["artwork"]["sha256"]:
            raise DraftError("Artwork changed; prepare a new approved revision.")
        before = read_json(directory / "before.json")
        if snapshot_digest(before) != review["before_fingerprint"]:
            raise DraftError("Baseline changed; prepare a new approved revision.")
        current = client.get_product(review["draft_id"])
        require_unpublished(current)
        verification_payload = {**review["payload"], "print_areas": before["print_areas"]}
        already_verified = False
        try:
            verify_update(before, current, verification_payload)
            already_verified = True
        except DraftError:
            pass
        if not already_verified:
            if snapshot_digest(current) != review["before_fingerprint"]:
                raise DraftError("Draft changed since review; inspect before preparing a new revision.")
            save_json(directory / "update-request.json", review["payload"])
            client.update_draft(review["draft_id"], review["payload"])
            current = client.get_product(review["draft_id"])
            save_json(directory / "after.json", current)
            verify_update(before, current, verification_payload)
        receipt = {
            "status": "already_verified" if already_verified else "verified",
            "product_id": current["id"], "revision": revision, "approval_id": approval.id,
            "url": "https://printify.com/app/product-details/" + current["id"],
            "selected_mockups": len(mockup_signature(current)),
            "enabled_variants": sum(v["is_enabled"] for v in current["variants"]),
            "dpi": review["artwork"]["dpi"], "published": False,
        }
        save_json(directory / "receipt.json", receipt)
        return receipt
