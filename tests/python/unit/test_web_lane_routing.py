"""Tests for the web build/ship lane primitives (F1).

Covers the new enum members and the supervisor's keyword routing: a web-build
goal lands in the WEB lane, a deploy/publish goal lands in the separate
WEBDEPLOY lane, and neither steals goals that belong to iOS or engineering.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from packages.schemas.product import ProductArtifactType, ProductPlatform
from packages.schemas.task_packet import Goal, WorkerLane
from packages.schemas.testing import TestLane


def _load_supervisor():
    path = Path(__file__).resolve().parents[3] / "apps" / "worker-supervisor" / "main.py"
    spec = importlib.util.spec_from_file_location("supervisor_main_web", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _goal(summary: str) -> Goal:
    return Goal(id="goal_x", title="t", summary=summary)


def test_new_enum_members_exist() -> None:
    assert WorkerLane.WEB.value == "web"
    assert WorkerLane.WEBDEPLOY.value == "webdeploy"
    assert ProductPlatform.WEB.value == "web"
    assert TestLane.WEB.value == "web"
    assert ProductArtifactType.WEB_ARCHITECTURE.value == "web_architecture"


def test_web_build_goal_routes_to_web_lane() -> None:
    sup = _load_supervisor()
    for summary in (
        "Build a landing page for the new wedge",
        "Create a marketing site with a waitlist",
        "Scaffold an Astro frontend for the product",
    ):
        (task,) = sup.plan_goal(_goal(summary))
        assert task.lane is WorkerLane.WEB, summary
        assert task.test_lane is TestLane.WEB
        assert task.tests_required is True


def test_deploy_goal_routes_to_separate_webdeploy_lane() -> None:
    sup = _load_supervisor()
    for summary in (
        "Deploy the site to production",
        "Publish the landing page on Netlify",
        "Go live with the marketing site",
    ):
        (task,) = sup.plan_goal(_goal(summary))
        assert task.lane is WorkerLane.WEBDEPLOY, summary
        # Deploy is high blast radius — it must request approval.
        assert task.requires_approval is True


def test_web_keywords_do_not_steal_ios_or_appstore_goals() -> None:
    sup = _load_supervisor()
    (ios,) = sup.plan_goal(_goal("Add a SwiftUI widget to the iPhone app"))
    assert ios.lane is WorkerLane.IOS
    (store,) = sup.plan_goal(_goal("Prepare the App Store submission"))
    assert store.lane is WorkerLane.APPSTORE


def test_generic_goal_still_routes_to_engineering() -> None:
    sup = _load_supervisor()
    (task,) = sup.plan_goal(_goal("Refactor the queue module"))
    assert task.lane is WorkerLane.ENGINEERING
