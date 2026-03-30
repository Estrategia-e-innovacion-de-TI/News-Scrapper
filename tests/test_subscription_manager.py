"""Unit tests for SubscriptionManager."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from extractor.capabilities.subscription import Subscriber, SubscriptionManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def terms_file(tmp_path: Path) -> Path:
    """Create a minimal terms_vigilancia.yaml with known groups."""
    p = tmp_path / "terms_vigilancia.yaml"
    p.write_text(
        textwrap.dedent("""\
        ia_ml:
          terms: ["machine learning", "deep learning"]
        ciberseguridad:
          terms: ["ransomware", "phishing"]
        blockchain:
          terms: ["blockchain", "DeFi"]
        """),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def subscribers_file(tmp_path: Path) -> Path:
    """Create a subscribers.yaml with two subscribers."""
    p = tmp_path / "subscribers.yaml"
    data = {
        "subscribers": [
            {"email": "alice@example.com", "name": "Alice", "query_groups": ["ia_ml", "ciberseguridad"]},
            {"email": "bob@example.com", "name": "Bob", "query_groups": ["blockchain"]},
        ]
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests — basic loading
# ---------------------------------------------------------------------------

class TestSubscriptionManagerLoading:
    def test_loads_subscribers(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        assert len(mgr.subscribers) == 2
        assert mgr.has_subscribers_file is True

    def test_valid_groups_from_terms(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        assert mgr.valid_groups == {"ia_ml", "ciberseguridad", "blockchain"}

    def test_missing_subscribers_file(self, tmp_path: Path, terms_file: Path) -> None:
        """When subscribers.yaml doesn't exist, manager loads with no subscribers."""
        mgr = SubscriptionManager(
            subscribers_path=tmp_path / "nonexistent.yaml",
            terms_path=terms_file,
        )
        assert mgr.has_subscribers_file is False
        assert mgr.subscribers == []

    def test_empty_subscribers_list(self, tmp_path: Path, terms_file: Path) -> None:
        p = tmp_path / "subscribers.yaml"
        p.write_text("subscribers: []\n", encoding="utf-8")
        mgr = SubscriptionManager(subscribers_path=p, terms_path=terms_file)
        assert mgr.has_subscribers_file is True
        assert mgr.subscribers == []


# ---------------------------------------------------------------------------
# Tests — query_group validation
# ---------------------------------------------------------------------------

class TestQueryGroupValidation:
    def test_invalid_group_skipped(self, tmp_path: Path, terms_file: Path) -> None:
        p = tmp_path / "subscribers.yaml"
        data = {
            "subscribers": [
                {"email": "x@x.com", "name": "X", "query_groups": ["ia_ml", "nonexistent_group"]},
            ]
        }
        p.write_text(yaml.dump(data), encoding="utf-8")
        mgr = SubscriptionManager(subscribers_path=p, terms_path=terms_file)
        sub = mgr.subscribers[0]
        assert sub.query_groups == ["ia_ml"]

    def test_all_groups_invalid(self, tmp_path: Path, terms_file: Path) -> None:
        p = tmp_path / "subscribers.yaml"
        data = {
            "subscribers": [
                {"email": "x@x.com", "name": "X", "query_groups": ["fake1", "fake2"]},
            ]
        }
        p.write_text(yaml.dump(data), encoding="utf-8")
        mgr = SubscriptionManager(subscribers_path=p, terms_path=terms_file)
        sub = mgr.subscribers[0]
        assert sub.query_groups == []


# ---------------------------------------------------------------------------
# Tests — lookup methods
# ---------------------------------------------------------------------------

class TestLookupMethods:
    def test_get_subscribers_for_group(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        subs = mgr.get_subscribers_for_group("ia_ml")
        assert len(subs) == 1
        assert subs[0].email == "alice@example.com"

    def test_get_subscribers_for_group_multiple(self, tmp_path: Path, terms_file: Path) -> None:
        p = tmp_path / "subscribers.yaml"
        data = {
            "subscribers": [
                {"email": "a@a.com", "name": "A", "query_groups": ["ia_ml"]},
                {"email": "b@b.com", "name": "B", "query_groups": ["ia_ml", "blockchain"]},
            ]
        }
        p.write_text(yaml.dump(data), encoding="utf-8")
        mgr = SubscriptionManager(subscribers_path=p, terms_path=terms_file)
        subs = mgr.get_subscribers_for_group("ia_ml")
        assert len(subs) == 2

    def test_get_subscribers_for_unknown_group(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        assert mgr.get_subscribers_for_group("nonexistent") == []

    def test_get_groups_for_subscriber(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        groups = mgr.get_groups_for_subscriber("alice@example.com")
        assert groups == ["ia_ml", "ciberseguridad"]

    def test_get_groups_for_unknown_subscriber(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        assert mgr.get_groups_for_subscriber("nobody@example.com") == []

    def test_get_all_groups(self, subscribers_file: Path, terms_file: Path) -> None:
        mgr = SubscriptionManager(subscribers_path=subscribers_file, terms_path=terms_file)
        assert mgr.get_all_groups() == ["blockchain", "ciberseguridad", "ia_ml"]


# ---------------------------------------------------------------------------
# Tests — capability registration
# ---------------------------------------------------------------------------

class TestCapabilityRegistration:
    def test_registered_in_registry(self) -> None:
        from extractor.capabilities.registry import get_capability
        cap = get_capability("subscription_manager")
        assert cap is not None
        assert cap.name == "subscription_manager"
        assert callable(cap.callable)
