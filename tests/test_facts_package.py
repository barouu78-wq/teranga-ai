"""Chargement automatique des repères par thème (services/facts/*.py)."""

import os
import re
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import facts, practical_facts  # noqa: E402


def test_collect_merges_topics_and_priorities_in_order():
    a = SimpleNamespace(TOPICS=(("aaa", r"\baaa\b", ("fait a",)),), SPECIFIC_FIRST=("aaa",))
    b = SimpleNamespace(TOPICS=(("bbb", r"\bbbb\b", ("fait b",)),))
    c = SimpleNamespace()  # un module sans sujet est ignoré
    topics, specific = facts._collect([a, b, c])
    assert [t[0] for t in topics] == ["aaa", "bbb"]
    assert specific == ("aaa",)


def test_all_topics_are_well_formed_and_unique():
    names = [name for name, _, _ in practical_facts.TOPICS]
    assert len(names) == len(set(names)), "nom de sujet en double"
    for name, pattern, items in practical_facts.TOPICS:
        assert re.fullmatch(r"[a-z0-9_]+", name), name
        re.compile(pattern)
        assert items and all(isinstance(item, str) and item.strip() and "<" not in item for item in items), name


def test_every_specific_first_name_is_a_real_topic():
    names = {name for name, _, _ in practical_facts.TOPICS}
    assert set(practical_facts._SPECIFIC_FIRST) <= names


def test_extra_topics_are_appended_after_the_core_ones():
    extra = facts.load_topics()[0]
    assert practical_facts.TOPICS[len(practical_facts.TOPICS) - len(extra):] == extra
