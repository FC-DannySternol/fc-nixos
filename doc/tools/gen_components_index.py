"""Generate the components overview ``src/components/index.md``.

Input is the flat component tree ``src/components/<name>.md``. One
fact is parsed per page: the first ``# `` heading -- its text with
the attribute block (``{ #nixos-... }``) stripped becomes the
bullet title.

Skipped on purpose:

* ``index.md`` -- the overview never lists itself;
* tombstones -- pages carrying the :data:`TOMBSTONE_MARKER` of
  :mod:`tools.scaffold_page` are removed components; their nav
  labels already read ``... (removed)`` and the version switcher,
  not the overview, is their access path.

Output is ``src/components/index.md``: H1 ``# Components {
#components }``, a one-line intro, and one bullet per component --
filename-sorted, links as bare ``<name>.md`` (same directory, so
zensical's LinksExtension rewrites them to ``.html`` and
link-validates them). The file is COMMITTED (generated, never
hand-edited); regenerate via ``python -m tools.gen_components_index``
-- or never think about it: :func:`tools.scaffold_page.scaffold`
and :func:`tools.scaffold_page.remove_page` refresh the overview
automatically, and ``make check`` (the real-tree no-diff test in
``tests/test_gen_components_index.py``) enforces freshness.

A missing ``components/`` tree or a component page without an H1
fails the run LOUDLY (exit 1) naming the offending page.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

import structlog

from tools._cli import DOC_ROOT, configure_cli_logging
from tools.scaffold_page import TOMBSTONE_MARKER

log = structlog.get_logger()

# First ``# `` heading of a page; the optional trailing attribute
# block ({ #anchor key=val }) is part of the heading syntax, not the
# title.
H1_RE = re.compile(r"^# (?P<title>.+?)(?:\s*\{[^}]*\})?\s*$", re.MULTILINE)

INTRO = (
    "All platform components documented in this manual, one page per "
    "component; the sidebar navigation groups them by topic."
)

INDEX_NAME = "index.md"


class ComponentsIndexError(Exception):
    """Missing ``components/`` tree or a component page without an H1
    heading. :func:`main` maps it to exit code 1."""


def scan_components(components: Path) -> list[tuple[str, str]]:
    """All listable component pages as ``(filename, title)`` pairs,
    filename-sorted.

    Skips ``index.md`` (never self-listed) and tombstones (removed
    components -- see module docstring). A page without an H1 fails
    loudly naming the page.
    """
    pages: list[tuple[str, str]] = []
    for page in sorted(components.glob("*.md")):
        if page.name == INDEX_NAME:
            continue
        text = page.read_text()
        if TOMBSTONE_MARKER in text:
            log.info(
                "page-skipped",
                page=page.name,
                reason="tombstone (removed component)",
            )
            continue
        h1 = H1_RE.search(text)
        if h1 is None:
            msg = f"no H1 heading found in {page}"
            raise ComponentsIndexError(msg)
        pages.append((page.name, h1.group("title")))
    return pages


def _render_bullets(pages: Sequence[tuple[str, str]]) -> str:
    """The complete ``index.md`` for an already-scanned page list."""
    lines = ["# Components { #components }", "", INTRO]
    lines += ["", *[f"- [{title}]({name})" for name, title in pages]]
    return "\n".join(lines) + "\n"


def render_index(src: Path) -> str:
    """Render the complete ``components/index.md`` of the *src* tree."""
    components = src / "components"
    if not components.is_dir():
        msg = f"missing components tree: {components}"
        raise ComponentsIndexError(msg)
    return _render_bullets(scan_components(components))


def regenerate(src: Path) -> Path:
    """Idempotently write the overview for the *src* tree.

    Logs ``index-written`` / ``index-unchanged``; returns the index
    path. Raises :class:`ComponentsIndexError` on a missing
    components tree or a missing H1 (both are loud failures).
    """
    components = src / "components"
    if not components.is_dir():
        msg = f"missing components tree: {components}"
        raise ComponentsIndexError(msg)
    pages = scan_components(components)
    index = components / INDEX_NAME
    rendered = _render_bullets(pages)
    if index.exists() and index.read_text() == rendered:
        log.info("index-unchanged", index=str(index), components=len(pages))
    else:
        index.write_text(rendered)
        log.info("index-written", index=str(index), components=len(pages))
    return index


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry: ``python -m tools.gen_components_index``.

    Exit codes: ``0`` (overview regenerated or already up to date),
    ``1`` (missing ``components/`` tree, or a component page without
    an H1 heading).
    """
    configure_cli_logging()
    parser = argparse.ArgumentParser(
        prog="gen_components_index",
        description=(
            "Generate src/components/index.md: the filename-sorted "
            "component overview the Components nav group links as its "
            "Overview entry."
        ),
    )
    parser.add_argument("--src", type=Path, default=DOC_ROOT / "src")
    args = parser.parse_args(argv)

    components = args.src / "components"
    if not components.is_dir():
        log.error("components-missing", components=str(components))
        return 1

    try:
        regenerate(args.src)
    except ComponentsIndexError as exc:
        log.exception("gen-components-index-failed", error=str(exc))
        return 1
    log.info("gen-components-index-done", components=str(components))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
