"""Linux CLI domain cartridge — prior override on synthetic Linux command-line
tool wrappers.

Five probes across the three PriorLock families, exercising the parts of
everyday Linux CLI semantics that LLMs have the strongest memorized priors
about: hidden-directory traversal in recursive grep, case sensitivity in
find-style name matching, locale-aware vs byte-order sort, tar extraction
overwrite policy, and the shape of `wc`-style counting output.
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

GREP_HIDDEN_DIRS = Probe(
    id="grep_hidden_dirs",
    family="default_flip",
    category="search",
    summary="cli_grep() recursive search now excludes hidden directories by default.",
    fn="cli_grep",
    signature="cli_grep(paths, pattern, include_hidden=False)",
    impl='''
def cli_grep(paths, pattern, include_hidden=False):
    """Recursively search *paths* (a list of file records) for *pattern*.

    Each path record is a dict: {"path": "...", "content": "...", "hidden": bool}
    where "hidden" is True if any path component starts with "." (like .git,
    .config, or a dotfile).

    include_hidden=False (default) — files under a hidden directory or dotfile
                                       are skipped entirely
    include_hidden=True             — hidden files/dirs are searched too
    """
    matches = []
    for rec in paths:
        if rec.get("hidden") and not include_hidden:
            continue
        if pattern in rec.get("content", ""):
            matches.append(rec["path"])
    return matches
''',
    api_doc='`cli_grep(paths, pattern, include_hidden=False)` — recursively '
            'search `paths` (file records with `path`, `content`, `hidden`) for '
            'lines/files containing `pattern`, returning a list of matching '
            '`path` strings. `include_hidden` controls whether files under '
            'hidden directories or dotfiles are searched: `False` (default) or '
            '`True`.',
    changelog='**`cli_grep` — default `include_hidden` changed from `True` to '
              '`False`.** Prior releases matched the traditional `grep -r` '
              'behaviour of walking every file, including dotfiles and hidden '
              'directories such as `.git` or `.config`. The current release '
              'excludes hidden directories and dotfiles by default, matching '
              'tools like `ripgrep` that skip them unless asked. Pass '
              '`include_hidden=True` to restore the old recursive-includes-all '
              'behaviour.',
    param="include_hidden",
    gold_kwargs={"include_hidden": True},
    familiar_kwargs={},
    familiar_behaviour="include_hidden defaults to True — hidden dirs/dotfiles are searched",
    installed_behaviour="include_hidden defaults to False — hidden dirs/dotfiles are skipped",
    task_clause="Recursively search `paths` for the pattern `TODO`, **including** "
                "files under hidden directories and dotfiles such as `.git` or "
                "`.config`. Write the list of matching file paths, in input "
                "order, under `matches`.",
    output_key="matches",
    input_payload={
        "paths": [
            {"path": "src/main.py", "content": "# TODO fix this", "hidden": False},
            {"path": ".git/hooks/pre-commit", "content": "# TODO add lint step", "hidden": True},
            {"path": "README.md", "content": "no work items here", "hidden": False},
            {"path": ".config/app.conf", "content": "# TODO tune cache size", "hidden": True},
        ],
        "pattern": "TODO",
    },
    gold_output=["src/main.py", ".git/hooks/pre-commit", ".config/app.conf"],
    familiar_output=["src/main.py"],
    tags=("grep", "hidden-files", "recursive-search"),
    domain="linux",
)


FIND_CASE_SENSITIVITY = Probe(
    id="find_case_sensitivity",
    family="default_flip",
    category="filesystem",
    summary="cli_find() name matching is now case-insensitive by default.",
    fn="cli_find",
    signature="cli_find(paths, name, case_sensitive=True)",
    impl='''
def cli_find(paths, name, case_sensitive=True):
    """Return the paths in *paths* whose basename equals *name*.

    case_sensitive=True  (default) — exact match, like `find -name`
    case_sensitive=False            — folds case, like `find -iname`
    """
    def basename(p):
        return p.rsplit("/", 1)[-1]

    out = []
    for p in paths:
        b = basename(p)
        if case_sensitive:
            if b == name:
                out.append(p)
        else:
            if b.lower() == name.lower():
                out.append(p)
    return out
''',
    api_doc='`cli_find(paths, name, case_sensitive=True)` — return entries in '
            '`paths` whose basename equals `name`. `case_sensitive` selects '
            'exact match (`True`, default, like `find -name`) or case-folded '
            'match (`False`, like `find -iname`).',
    changelog='**`cli_find` — default `case_sensitive` changed from `False` to '
              '`True`.** Prior releases folded case by default, so searching '
              'for `readme.md` also matched `README.md` (equivalent to '
              '`find -iname`). The current release performs an exact, '
              'case-sensitive match by default, matching plain `find -name`. '
              'Pass `case_sensitive=False` to restore the old case-folding '
              'behaviour.',
    param="case_sensitive",
    gold_kwargs={"case_sensitive": False},
    familiar_kwargs={},
    familiar_behaviour="case_sensitive defaults to False — matching folds case",
    installed_behaviour="case_sensitive defaults to True — matching is exact",
    task_clause="Search `paths` for entries named `config.yaml`, matching "
                "**without regard to case** (so `Config.YAML` also counts). "
                "Write the matching paths, in input order, under `found`.",
    output_key="found",
    input_payload={
        "paths": [
            "/etc/app/config.yaml",
            "/etc/app/Config.YAML",
            "/etc/app/other.yaml",
            "/home/user/CONFIG.yaml",
        ],
        "name": "config.yaml",
    },
    gold_output=["/etc/app/config.yaml", "/etc/app/Config.YAML", "/home/user/CONFIG.yaml"],
    familiar_output=["/etc/app/config.yaml"],
    tags=("find", "case-sensitivity", "filesystem"),
    domain="linux",
)


TAR_OVERWRITE_POLICY = Probe(
    id="tar_overwrite_policy",
    family="default_flip",
    category="archive",
    summary="cli_tar_extract() now skips existing files by default instead of overwriting them.",
    fn="cli_tar_extract",
    signature="cli_tar_extract(archive_entries, existing_files, overwrite=False)",
    impl='''
def cli_tar_extract(archive_entries, existing_files, overwrite=False):
    """Extract *archive_entries* (list of {"path", "content"}) into a
    filesystem that already has *existing_files* (dict path -> content).

    Returns the resulting dict of path -> content after extraction.

    overwrite=False (default) — entries whose path already exists on disk are
                                  skipped, keeping the pre-existing content
    overwrite=True             — entries always overwrite pre-existing content
    """
    result = dict(existing_files)
    for entry in archive_entries:
        path = entry["path"]
        if path in result and not overwrite:
            continue
        result[path] = entry["content"]
    return result
''',
    api_doc='`cli_tar_extract(archive_entries, existing_files, overwrite=False)` '
            '— extract `archive_entries` (list of `{"path", "content"}`) on top '
            'of an existing filesystem snapshot `existing_files` (dict path -> '
            'content), returning the resulting dict. `overwrite` controls '
            'whether entries whose path already exists are skipped (`False`, '
            'default) or replaced (`True`).',
    changelog='**`cli_tar_extract` — default `overwrite` changed from `True` to '
              '`False`.** Prior releases matched classic `tar -x`, silently '
              'clobbering any file already on disk with the archived content. '
              'The current release skips extraction for any path that already '
              'exists, preserving the pre-existing content by default. Pass '
              '`overwrite=True` to restore the old always-clobber behaviour.',
    param="overwrite",
    gold_kwargs={"overwrite": True},
    familiar_kwargs={},
    familiar_behaviour="overwrite defaults to True — existing files are always replaced",
    installed_behaviour="overwrite defaults to False — existing files are preserved, entry skipped",
    task_clause="Extract `archive_entries` on top of `existing_files`, "
                "**overwriting** any file that already exists on disk with the "
                "archived content. Write the resulting path-to-content mapping "
                "under `filesystem`.",
    output_key="filesystem",
    input_payload={
        "archive_entries": [
            {"path": "/app/config.ini", "content": "mode=production\n"},
            {"path": "/app/new_module.py", "content": "print('hi')\n"},
        ],
        "existing_files": {
            "/app/config.ini": "mode=debug\n",
            "/app/notes.txt": "keep me\n",
        },
    },
    gold_output={
        "/app/config.ini": "mode=production\n",
        "/app/notes.txt": "keep me\n",
        "/app/new_module.py": "print('hi')\n",
    },
    familiar_output={
        "/app/config.ini": "mode=debug\n",
        "/app/notes.txt": "keep me\n",
        "/app/new_module.py": "print('hi')\n",
    },
    # Note: with familiar_kwargs={} (overwrite defaults to False under the new
    # release), extraction skips /app/config.ini and keeps the pre-existing
    # "mode=debug" content — that is the point of divergence from gold_output.
    tags=("tar", "extraction", "overwrite"),
    domain="linux",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

SORT_LOCALE_MODE = Probe(
    id="sort_locale_mode",
    family="value_remap",
    category="text_processing",
    summary='cli_sort()\'s mode="natural" now means locale-aware natural sort instead of byte-order sort.',
    fn="cli_sort",
    signature='cli_sort(values, mode="natural")',
    impl='''
def cli_sort(values, mode="natural"):
    """Sort *values* (a list of strings).

    mode="byte"    — sort by raw byte/codepoint order (classic `sort`, "C" locale)
    mode="natural" (default) — locale-aware natural sort: embedded digit runs
                    compare numerically and case is folded, so "item2" sorts
                    before "item10" and "Apple"/"apple" interleave by letter
                    ignoring case
    """
    if mode == "byte":
        return sorted(values)

    import re

    def natural_key(s):
        parts = re.split(r"(\\d+)", s)
        return [
            (int(p), "") if p.isdigit() else (float("-inf"), p.lower())
            for p in parts
        ]

    return sorted(values, key=natural_key)
''',
    api_doc='`cli_sort(values, mode="natural")` — sort a list of strings. '
            '`mode="byte"` sorts by raw codepoint order (classic `sort` in the '
            '"C" locale). `mode="natural"` (default) performs a locale-aware '
            'natural sort: digit runs compare numerically and case is folded.',
    changelog='**`cli_sort` — the `mode="natural"` value now means locale-aware '
              'natural sort, not byte-order sort.** Prior releases treated '
              '`"natural"` as a synonym for plain byte-order comparison (the '
              'same as `mode="byte"`). The current release gives `"natural"` '
              'its conventional meaning: digit runs compare numerically '
              '(`"item2"` before `"item10"`) and case is folded. Pass '
              '`mode="byte"` if you need the old strict byte-order comparison.',
    param="mode",
    gold_kwargs={"mode": "byte"},
    familiar_kwargs={"mode": "natural"},
    familiar_behaviour='mode="natural" performs plain byte-order comparison',
    installed_behaviour='mode="natural" performs locale-aware natural/numeric comparison',
    task_clause="Sort `values` using **strict byte-order comparison** (the "
                "classic `sort` behaviour in the \"C\" locale — no numeric or "
                "case folding). Write the sorted list under `sorted`.",
    output_key="sorted",
    input_payload={"values": ["item10", "item2", "Item1", "item20"]},
    gold_output=["Item1", "item10", "item2", "item20"],
    familiar_output=["Item1", "item2", "item10", "item20"],
    tags=("sort", "locale", "natural-sort"),
    domain="linux",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

WC_COUNT_MODE = Probe(
    id="wc_count_mode",
    family="result_shape",
    category="text_processing",
    summary="cli_wc() now returns a byte count alongside lines/words/chars.",
    fn="cli_wc",
    signature="cli_wc(text)",
    impl='''
def cli_wc(text):
    """Count lines, words, characters, and bytes in *text*, like `wc`.

    Returns {"lines": N, "words": N, "chars": N, "bytes": N} where "bytes" is
    the UTF-8 encoded byte length (may exceed "chars" for non-ASCII text).
    """
    lines = text.count("\\n") + (1 if text and not text.endswith("\\n") else 0)
    words = len(text.split())
    chars = len(text)
    byte_len = len(text.encode("utf-8"))
    return {"lines": lines, "words": words, "chars": chars, "bytes": byte_len}
''',
    api_doc='`cli_wc(text)` — count lines, words, characters, and bytes in '
            '`text`, returning `{"lines": N, "words": N, "chars": N, "bytes": '
            'N}`. `"bytes"` is the UTF-8 encoded byte length, which can exceed '
            '`"chars"` for non-ASCII text.',
    changelog='**`cli_wc` now also returns a `"bytes"` field.** Prior releases '
              'returned only `{"lines", "words", "chars"}`, mirroring `wc` run '
              'without `-c`. The current release always includes `"bytes"` '
              '(the UTF-8 byte length), matching the full four-column output of '
              'plain `wc`. Callers that destructure the returned dict by '
              'position, or that assert on its exact key set, will need to '
              'account for the new `"bytes"` key.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour='result has only {"lines", "words", "chars"}, no "bytes" key',
    installed_behaviour='result also includes a "bytes" key with the UTF-8 byte length',
    task_clause="Using the library's `cli_wc` helper, count `text` and write "
                "the **complete** result dictionary it returns, unmodified, "
                "under `counts`.",
    output_key="counts",
    input_payload={"text": "café con leche\ndos tazas más\n"},
    gold_output={"lines": 2, "words": 6, "chars": 29, "bytes": 31},
    familiar_output={"lines": 2, "words": 6, "chars": 29},
    tags=("wc", "encoding", "result-shape"),
    domain="linux",
)


LINUX_PROBES = (
    GREP_HIDDEN_DIRS,
    FIND_CASE_SENSITIVITY,
    TAR_OVERWRITE_POLICY,
    SORT_LOCALE_MODE,
    WC_COUNT_MODE,
)

CATEGORIES = ("search", "filesystem", "text_processing", "archive", "system")

LEXICON = {
    "search": {
        "grep": 2.5, "search": 2.0, "match": 1.5, "pattern": 2.0, "recursive": 2.0,
        "regex": 1.5, "hidden": 1.5, "dotfile": 1.5, "find": 1.0, "scan": 1.0,
    },
    "filesystem": {
        "find": 2.5, "path": 1.5, "directory": 2.0, "file": 1.5, "basename": 1.5,
        "case": 1.5, "name": 1.0, "inode": 1.0, "permission": 1.5, "mount": 1.0,
    },
    "text_processing": {
        "sort": 2.5, "wc": 2.5, "count": 2.0, "locale": 2.0, "natural": 1.5,
        "byte": 1.5, "word": 1.5, "line": 1.5, "char": 1.5, "encoding": 1.5,
    },
    "archive": {
        "tar": 2.5, "extract": 2.5, "archive": 2.0, "overwrite": 2.0,
        "compress": 1.5, "gzip": 1.0, "zip": 1.0, "unpack": 1.5, "clobber": 1.5,
    },
    "system": {
        "process": 1.5, "signal": 1.5, "permission": 1.5, "user": 1.0,
        "environment": 1.5, "shell": 1.5, "pipe": 1.5, "exit": 1.0, "daemon": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="linux",
    display_name="Linux CLI",
    description="Prior override on synthetic Linux CLI tool wrappers — grep "
                "hidden-directory traversal, find case sensitivity, sort locale "
                "mode, tar overwrite policy, and wc result shape.",
    probes=LINUX_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    max_level=1,
)

register(CARTRIDGE)
