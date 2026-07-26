"""Deep SQL grading — SQLite execution wrappers for SQL probes.

Each verifier creates an in-memory SQLite database, populates it with the
probe's input data, executes the query under both gold and familiar semantics,
and compares the agent's output against real database results.

This module provides ``attach_deep_grading()`` which patches the SQL cartridge's
probes with SQLite-backed verification functions.  Called by the engine when
``--deep-grade`` is enabled.

Usage::

    from priorlock.cartridges.deep_sql import attach_deep_grading
    attach_deep_grading()  # patches sql cartridge probes in place
"""
from __future__ import annotations

import sqlite3
from typing import Any


# ─── Verifier functions ─────────────────────────────────────────────────────
# Each takes the agent's output and returns (matches_gold: bool, detail: str).


def verify_null_group_policy(agent_output: Any) -> tuple[bool, str]:
    """Verify GROUP BY NULL handling against real SQLite."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (region TEXT, amount INTEGER)")
    cur.executemany("INSERT INTO t VALUES (?, ?)", [
        ("west", 10), ("east", 20), (None, 5), ("west", 7), (None, 3),
    ])

    # Gold: exclude NULLs (WHERE region IS NOT NULL GROUP BY region)
    cur.execute(
        "SELECT region AS key, COUNT(*) AS count FROM t "
        "WHERE region IS NOT NULL GROUP BY region ORDER BY rowid"
    )
    gold_rows = [{"key": r[0], "count": r[1]} for r in cur.fetchall()]

    # Familiar: include NULLs (GROUP BY region without filter)
    cur.execute(
        "SELECT region AS key, COUNT(*) AS count FROM t "
        "GROUP BY region ORDER BY MIN(rowid)"
    )
    familiar_rows = [{"key": r[0], "count": r[1]} for r in cur.fetchall()]

    conn.close()

    if agent_output == gold_rows:
        return True, f"matches SQLite gold: {gold_rows}"
    if agent_output == familiar_rows:
        return False, f"matches SQLite familiar (prior-locked): {familiar_rows}"
    return False, f"matches neither. SQLite gold={gold_rows}, familiar={familiar_rows}"


def verify_join_null_match(agent_output: Any) -> tuple[bool, str]:
    """Verify JOIN NULL matching against real SQLite."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE left_t (id INTEGER, code TEXT)")
    cur.execute("CREATE TABLE right_t (id INTEGER, code TEXT)")
    cur.executemany("INSERT INTO left_t VALUES (?, ?)", [
        (1, "A"), (2, None), (3, "B"),
    ])
    cur.executemany("INSERT INTO right_t VALUES (?, ?)", [
        (10, "A"), (11, None), (12, "C"),
    ])

    # Gold: standard SQL — NULL never matches NULL
    cur.execute(
        "SELECT l.id AS left_id, r.id AS right_id "
        "FROM left_t l INNER JOIN right_t r ON l.code = r.code"
    )
    gold_rows = [{"left_id": r[0], "right_id": r[1]} for r in cur.fetchall()]

    # Familiar: NULL matches NULL (non-standard)
    cur.execute(
        "SELECT l.id AS left_id, r.id AS right_id "
        "FROM left_t l INNER JOIN right_t r ON l.code IS r.code"
    )
    familiar_rows = [{"left_id": r[0], "right_id": r[1]} for r in cur.fetchall()]

    conn.close()

    if agent_output == gold_rows:
        return True, f"matches SQLite gold: {gold_rows}"
    if agent_output == familiar_rows:
        return False, f"matches SQLite familiar (prior-locked): {familiar_rows}"
    return False, f"matches neither. SQLite gold={gold_rows}, familiar={familiar_rows}"


def verify_distinct_case_mode(agent_output: Any) -> tuple[bool, str]:
    """Verify DISTINCT case sensitivity against real SQLite."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (val TEXT)")
    cur.executemany("INSERT INTO t VALUES (?)", [
        ("Apple",), ("apple",), ("Banana",), ("BANANA",), ("Cherry",),
    ])

    # Gold: case-sensitive DISTINCT (SQLite default)
    cur.execute("SELECT DISTINCT val FROM t ORDER BY rowid")
    gold_rows = [r[0] for r in cur.fetchall()]

    # Familiar: case-folded (simulated via LOWER)
    cur.execute(
        "SELECT val FROM t GROUP BY LOWER(val) ORDER BY MIN(rowid)"
    )
    familiar_rows = [r[0] for r in cur.fetchall()]

    conn.close()

    if agent_output == gold_rows:
        return True, f"matches SQLite gold: {gold_rows}"
    if agent_output == familiar_rows:
        return False, f"matches SQLite familiar (prior-locked): {familiar_rows}"
    return False, f"matches neither. SQLite gold={gold_rows}, familiar={familiar_rows}"


def verify_order_nulls_position(agent_output: Any) -> tuple[bool, str]:
    """Verify ORDER BY NULLS FIRST/LAST against real SQLite."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (id INTEGER, amount INTEGER)")
    cur.executemany("INSERT INTO t VALUES (?, ?)", [
        (1, 30), (2, None), (3, 10), (4, None), (5, 20),
    ])

    # Gold: NULLS FIRST
    cur.execute(
        "SELECT id FROM t ORDER BY "
        "CASE WHEN amount IS NULL THEN 0 ELSE 1 END, amount ASC"
    )
    gold_ids = [r[0] for r in cur.fetchall()]

    # Familiar: NULLS LAST (SQLite default)
    cur.execute("SELECT id FROM t ORDER BY amount ASC")
    familiar_ids = [r[0] for r in cur.fetchall()]

    conn.close()

    if agent_output == gold_ids:
        return True, f"matches SQLite gold: {gold_ids}"
    if agent_output == familiar_ids:
        return False, f"matches SQLite familiar (prior-locked): {familiar_ids}"
    return False, f"matches neither. SQLite gold={gold_ids}, familiar={familiar_ids}"


def verify_coalesce_empty_string(agent_output: Any) -> tuple[bool, str]:
    """Verify COALESCE empty-string handling against real SQLite."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (val TEXT)")
    cur.executemany("INSERT INTO t VALUES (?)", [
        (None,), ("",), ("fallback",),
    ])

    # Gold: COALESCE treats "" as non-NULL (SQLite standard behavior)
    cur.execute("SELECT COALESCE(val, 'NONE') FROM t WHERE val IS NOT NULL LIMIT 1")
    gold_result = cur.fetchone()[0]

    # Direct COALESCE over the values
    cur.execute(
        "SELECT COALESCE("
        "  (SELECT val FROM t WHERE rowid=1),"
        "  (SELECT val FROM t WHERE rowid=2),"
        "  (SELECT val FROM t WHERE rowid=3)"
        ")"
    )
    coalesce_result = cur.fetchone()[0]

    conn.close()

    if agent_output == coalesce_result:
        return True, f"matches SQLite COALESCE result: {coalesce_result!r}"
    if agent_output == "fallback":
        return False, "matches familiar behavior (skipped empty string)"
    return False, f"matches neither. SQLite COALESCE={coalesce_result!r}"


# ─── Registry of deep verifiers ─────────────────────────────────────────────

DEEP_VERIFIERS: dict[str, Any] = {
    "null_group_policy": verify_null_group_policy,
    "join_null_match": verify_join_null_match,
    "distinct_case_mode": verify_distinct_case_mode,
    "order_nulls_position": verify_order_nulls_position,
    "coalesce_empty_string": verify_coalesce_empty_string,
}


def attach_deep_grading() -> None:
    """Patch SQL cartridge probes with SQLite-backed deep verification.

    After calling this, each SQL probe gains a ``deep_verify`` attribute —
    a callable that takes the agent's output and returns ``(is_gold, detail)``.
    """
    from . import get

    spec = get("sql")
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            # Frozen dataclass — store on the module-level registry instead
            object.__setattr__(probe, "_deep_verifier", DEEP_VERIFIERS[probe.id])


def deep_verify(probe_id: str, agent_output: Any) -> tuple[bool, str]:
    """Run the deep SQLite verifier for a probe, if one exists.

    Returns (matches_gold, detail_string).
    Raises KeyError if no deep verifier is registered for this probe.
    """
    if probe_id not in DEEP_VERIFIERS:
        raise KeyError(f"no deep verifier for probe {probe_id!r}")
    return DEEP_VERIFIERS[probe_id](agent_output)


def run_all_deep_checks() -> dict[str, tuple[bool, str]]:
    """Run every deep verifier with its probe's gold_output. Useful for CI.

    Returns {probe_id: (passed, detail)} where passed=True means
    the probe's gold_output matches what SQLite produces.
    """
    from . import get

    spec = get("sql")
    results = {}
    for probe in spec.probes:
        if probe.id in DEEP_VERIFIERS:
            passed, detail = DEEP_VERIFIERS[probe.id](probe.gold_output)
            results[probe.id] = (passed, detail)
    return results
