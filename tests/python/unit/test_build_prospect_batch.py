"""Batch deploy + draft cleanup for build_prospect_site.py.

Covers the pure selection/clear helpers, the idempotent batch loop (skip vs
force), and the confirm-gated cleanup executor — all without touching Netlify
(the deploy + delete calls are faked).
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from packages.agency.prospect_site import PreviewResult, ProspectBuildError
from scripts.agency import build_prospect_site as bps


@pytest.fixture
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    records = tmp_path / "records"
    sites = tmp_path / "sites"
    records.mkdir()
    sites.mkdir()
    monkeypatch.setattr(bps, "RECORDS_DIR", records)
    monkeypatch.setattr(bps, "SITES_DIR", sites)
    # Default: nothing is suppressed unless a test says so.
    monkeypatch.setattr("packages.agency.suppression.is_suppressed", lambda rec, **k: False)
    return records, sites


def _rec(records: Path, place_id: str, **extra: object) -> dict:
    rec = {"place_id": place_id, "display_name": f"Biz {place_id}", **extra}
    (records / f"{place_id}.json").write_text(json.dumps(rec))
    return rec


def _built_site(sites: Path, place_id: str) -> None:
    dist = sites / place_id / "dist-v2"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")


# --------------------------------------------------------------- selection
def test_batch_place_ids_from_csv(state, tmp_path: Path) -> None:
    csv_path = tmp_path / "batch.csv"
    csv_path.write_text("place_id,name\np1,A\np2,B\np1,A-dup\n")
    assert bps._batch_place_ids(str(csv_path)) == ["p1", "p2"]  # ordered, de-duped


def test_batch_place_ids_from_glob(state) -> None:
    _, sites = state
    _built_site(sites, "p2")
    _built_site(sites, "p1")
    assert bps._batch_place_ids("*") == ["p1", "p2"]
    assert bps._batch_place_ids("p1*") == ["p1"]


def test_select_batch_records_skips_unknown_place_ids(state, tmp_path: Path, capsys) -> None:
    records, _ = state
    _rec(records, "p1")
    csv_path = tmp_path / "b.csv"
    csv_path.write_text("place_id\np1\npX\n")
    chosen = bps.select_batch_records(str(csv_path))
    assert [r["place_id"] for r in chosen] == ["p1"]
    assert "1 place_id(s) in batch have no warehouse record" in capsys.readouterr().out


# ------------------------------------------------------------- cleanup pick
def test_select_cleanup_targets(state, monkeypatch) -> None:
    records, _ = state
    _rec(records, "p_lost", engagement_status="lost", mockup_deploy_id="d1",
         mockup_url="https://x/lost")
    _rec(records, "p_supp", mockup_deploy_id="d2", mockup_url="https://x/supp")
    _rec(records, "p_active", mockup_deploy_id="d3", mockup_url="https://x/active")
    _rec(records, "p_lost_nodeploy", engagement_status="lost")  # no deploy id → skipped
    monkeypatch.setattr(
        "packages.agency.suppression.is_suppressed",
        lambda rec, **k: rec.get("place_id") == "p_supp",
    )
    targets = bps.select_cleanup_targets(bps._load_records())
    by_id = {rec["place_id"]: (deploy_id, reason) for rec, deploy_id, reason in targets}
    assert by_id == {"p_lost": ("d1", "lost"), "p_supp": ("d2", "suppressed")}


def test_clear_record_mockup_fields(state) -> None:
    records, _ = state
    _rec(records, "p1", mockup_url="https://x", mockup_site_id="s", mockup_deploy_id="d",
         mockup_version="v2-bespoke")
    bps.clear_record_mockup_fields("p1")
    rec = json.loads((records / "p1.json").read_text())
    assert "mockup_url" not in rec and "mockup_site_id" not in rec
    assert "mockup_deploy_id" not in rec
    assert rec["mockup_cleaned_at"]
    assert rec["mockup_version"] == "v2-bespoke"  # the build record is preserved


# ----------------------------------------------------------- cleanup runner
class _FakeTarget:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_deploy(self, deploy_id: str) -> None:
        self.deleted.append(deploy_id)


def test_cleanup_drafts_deletes_and_clears_on_confirm(state, monkeypatch, capsys) -> None:
    records, _ = state
    _rec(records, "p_lost", engagement_status="lost", mockup_deploy_id="d1",
         mockup_url="https://x/lost")
    fake = _FakeTarget()
    monkeypatch.setattr(bps, "make_target", lambda slug: (fake, None))
    monkeypatch.setattr(bps, "_confirm", lambda prompt: True)

    bps.cleanup_drafts(Namespace(account=None))

    assert fake.deleted == ["d1"]
    rec = json.loads((records / "p_lost.json").read_text())
    assert "mockup_url" not in rec  # record URL cleared
    assert "1 cleaned" in capsys.readouterr().out


def test_cleanup_drafts_aborts_without_confirm(state, monkeypatch, capsys) -> None:
    records, _ = state
    _rec(records, "p_lost", engagement_status="lost", mockup_deploy_id="d1",
         mockup_url="https://x/lost")
    fake = _FakeTarget()
    monkeypatch.setattr(bps, "make_target", lambda slug: (fake, None))
    monkeypatch.setattr(bps, "_confirm", lambda prompt: False)

    bps.cleanup_drafts(Namespace(account=None))

    assert fake.deleted == []  # nothing deleted
    rec = json.loads((records / "p_lost.json").read_text())
    assert rec["mockup_url"] == "https://x/lost"  # record untouched
    assert "Aborted" in capsys.readouterr().out


# ------------------------------------------------------------- batch loop
def test_batch_loop_skips_deployed_and_backfills(state, monkeypatch, capsys) -> None:
    records, sites = state
    _rec(records, "p1")  # not deployed → should deploy
    _rec(records, "p2", mockup_url="https://x/p2")  # already deployed → skip
    _built_site(sites, "p1")
    _built_site(sites, "p2")

    def fake_bespoke(rec, out_dir, target, account):
        pid = str(rec.get("place_id", ""))
        result = PreviewResult(
            place_id=pid, site_name="bbw-previews", dist_dir=out_dir / "dist-v2",
            deployed=True, mockup_url=f"https://x/{pid}", site_id="s", deploy_id=f"d-{pid}",
        )
        return result, "bespoke", [], None

    monkeypatch.setattr(bps, "_bespoke_deploy", fake_bespoke)
    monkeypatch.setattr(bps, "make_target", lambda slug: (object(), None))
    monkeypatch.setattr(bps.time, "sleep", lambda *a, **k: None)  # no real rate-limit wait
    monkeypatch.setattr(bps.sys, "argv", ["build_prospect_site.py", "--batch", "*", "--no-enrich"])

    bps.main()

    out = capsys.readouterr().out
    assert "deployed  1" in out
    assert "skipped   1" in out
    # p1 backfilled; p2 left as-is (skipped, not re-deployed)
    assert json.loads((records / "p1.json").read_text())["mockup_url"] == "https://x/p1"


def test_batch_force_redeploys_existing(state, monkeypatch, capsys) -> None:
    records, sites = state
    _rec(records, "p2", mockup_url="https://old/p2")
    _built_site(sites, "p2")

    def fake_bespoke(rec, out_dir, target, account):
        return (
            PreviewResult(place_id="p2", site_name="bbw-previews", dist_dir=out_dir / "dist-v2",
                          deployed=True, mockup_url="https://new/p2", site_id="s", deploy_id="d2"),
            "bespoke", [], None,
        )

    monkeypatch.setattr(bps, "_bespoke_deploy", fake_bespoke)
    monkeypatch.setattr(bps, "make_target", lambda slug: (object(), None))
    monkeypatch.setattr(bps.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(
        bps.sys, "argv", ["build_prospect_site.py", "--batch", "*", "--force", "--no-enrich"]
    )

    bps.main()

    assert "deployed  1" in capsys.readouterr().out
    assert json.loads((records / "p2.json").read_text())["mockup_url"] == "https://new/p2"


def test_batch_categorizes_scaffold_copy(state, monkeypatch, capsys) -> None:
    records, sites = state
    _rec(records, "p1")
    _built_site(sites, "p1")

    from packages.agency.prospect_site import ScaffoldCopyError

    def fake_bespoke(rec, out_dir, target, account):
        raise ScaffoldCopyError("index.html: scaffold copy 'category-safe'")

    monkeypatch.setattr(bps, "_bespoke_deploy", fake_bespoke)
    monkeypatch.setattr(bps, "make_target", lambda slug: (object(), None))
    monkeypatch.setattr(bps.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(bps.sys, "argv", ["build_prospect_site.py", "--batch", "*", "--no-enrich"])

    bps.main()

    out = capsys.readouterr().out
    assert "scaffold  1" in out
    assert "Needs attention" in out


def test_batch_categorizes_missing_build_as_no_build(state, monkeypatch, capsys) -> None:
    records, sites = state
    _rec(records, "p1")
    _built_site(sites, "p1")  # dir exists so glob matches…

    def fake_bespoke(rec, out_dir, target, account):
        raise ProspectBuildError("no bespoke build at dist-v2")

    monkeypatch.setattr(bps, "_bespoke_deploy", fake_bespoke)
    monkeypatch.setattr(bps, "make_target", lambda slug: (object(), None))
    monkeypatch.setattr(bps.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(bps.sys, "argv", ["build_prospect_site.py", "--batch", "*", "--no-enrich"])

    bps.main()

    out = capsys.readouterr().out
    assert "no-build  1" in out
    assert "Needs attention" in out
