"""Executable spec for ``tools/gen_components_index.py``.

The generator turns the flat component tree
``src/components/<name>.md`` into the committed overview
``src/components/index.md``. Properties that pin the design:

- ``render_index`` lists every component page filename-sorted as
  ``- [Title](<name>.md)`` bullets -- titles are the pages' H1 text
  with the attribute block (``{ #nixos-... }``) stripped, links are
  BARE same-directory ``.md`` targets so zensical's LinksExtension
  rewrites them to ``.html`` and link-validates them;
- ``index.md`` never lists itself; tombstones (pages carrying
  :data:`tools.scaffold_page.TOMBSTONE_MARKER`) are skipped --
  removed components stay reachable via nav label + version
  switcher, not via the overview;
- a component page without an H1 fails LOUDLY, naming the page;
- ``main`` writes the overview idempotently
  (``index-written`` / ``index-unchanged``) and exits ``1`` on a
  missing ``components/`` tree or a missing H1;
- the REAL tree is the freshness gate behind ``make check``:
  ``render_index`` must equal the committed ``src/components/
  index.md`` byte for byte, every component page must be listed,
  and the nav's Components group must lead with the Overview entry
  pointing at the generated page.

Fixture-tree tests run against tmp trees ONLY -- never against the
real ``doc/src`` tree (the two real-tree tests are the committed
contract itself).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pytest_readable import readable

from tests.helpers import DOC_ROOT as DOC
from tools import gen_components_index as gci
from tools.scaffold_page import TOMBSTONE_MARKER


def build_tree(src: Path) -> None:
    """Minimal component tree: three pages with attribute-block H1s,
    one tombstone, and a stale overview waiting to be replaced."""
    components = src / "components"
    components.mkdir(parents=True)
    (components / "webgateway.md").write_text(
        "# Webgateway (NGINX, HAProxy) { #nixos-webgateway }\n\nrole docs\n"
    )
    (components / "ferretdb.md").write_text("# FerretDB { #nixos-ferretdb }\n")
    (components / "postgresql.md").write_text("# PostgreSQL { #nixos-postgresql }\n")
    (components / "mysql.md").write_text(
        f"# MySQL {{ #nixos-mysql }}\n\n"
        f"{TOMBSTONE_MARKER}\n\n"
        "    This component is no longer part of the current platform\n"
        "    version.\n"
    )
    (components / "index.md").write_text("# stale overview\n")


def components_section(nav: list) -> list:
    """The value of the ``Components`` key of the parsed nav."""
    for item in nav:
        if isinstance(item, dict) and "Components" in item:
            return item["Components"]
    raise AssertionError("no Components section in nav")


@readable(
    intention="render_index lists all pages filename-sorted as bullets "
    "with bare relative .md links",
    steps=[
        "build the fixture tree",
        "render the overview",
        "compare the bullet block",
    ],
    criteria=[
        "H1 line '# Components { #components }'",
        "bullets sorted by file name: ferretdb, postgresql, webgateway",
        "links are bare <name>.md targets",
    ],
)
def test_render_filename_sorted_with_relative_links(tmp_path: Path) -> None:
    src = tmp_path / "src"
    build_tree(src)

    md = gci.render_index(src)

    lines = md.splitlines()
    assert lines[0] == "# Components { #components }"
    assert [ln for ln in lines if ln.startswith("- ")] == [
        "- [FerretDB](ferretdb.md)",
        "- [PostgreSQL](postgresql.md)",
        "- [Webgateway (NGINX, HAProxy)](webgateway.md)",
    ]


@readable(
    intention="titles come from the H1 with the attribute block stripped, "
    "text kept verbatim",
    steps=["render the fixture tree", "check title text and stripped attrs"],
    criteria=[
        "parenthesized titles survive verbatim",
        "no page anchor fragment ({ #nixos-...) anywhere in the overview",
    ],
)
def test_titles_from_h1_attr_block_stripped(tmp_path: Path) -> None:
    src = tmp_path / "src"
    build_tree(src)

    md = gci.render_index(src)

    assert "- [Webgateway (NGINX, HAProxy)](webgateway.md)" in md
    # the overview's own H1 anchor stays; the PAGES' anchors are stripped
    assert md.splitlines()[0] == "# Components { #components }"
    assert "{ #nixos-" not in md


@readable(
    intention="index.md is never self-listed; tombstoned pages are skipped",
    steps=[
        "render the fixture tree (carries a tombstoned mysql.md)",
        "check absence of both pages",
    ],
    criteria=[
        "no (index.md) link target",
        "no (mysql.md) link target while ferretdb stays listed",
    ],
)
def test_index_not_selflisted_tombstones_skipped(tmp_path: Path) -> None:
    src = tmp_path / "src"
    build_tree(src)

    md = gci.render_index(src)

    assert "(index.md)" not in md
    assert "(mysql.md)" not in md
    assert "(ferretdb.md)" in md


@readable(
    intention="a component page without an H1 fails loudly, naming the page",
    steps=[
        "add a page whose highest heading is an H2",
        "render_index must raise naming the page",
        "main must exit 1 with the page name on stderr",
    ],
    criteria=[
        "ComponentsIndexError names broken.md",
        "main returns 1",
        "broken.md appears in stderr",
    ],
)
def test_missing_h1_fails_loudly_naming_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    build_tree(src)
    (src / "components" / "broken.md").write_text("## only an H2\n")

    with pytest.raises(gci.ComponentsIndexError, match=r"broken\.md"):
        gci.render_index(src)

    assert gci.main(["--src", str(src)]) == 1
    assert "broken.md" in capsys.readouterr().err


@readable(
    intention="regeneration is idempotent: first run writes, second is a no-op",
    steps=[
        "run main twice against the fixture tree",
        "compare the overview bytes and the logged events",
    ],
    criteria=[
        "exit 0 both times",
        "first run logs index-written, second index-unchanged",
        "overview byte-identical after the second run",
    ],
)
def test_regeneration_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    build_tree(src)

    assert gci.main(["--src", str(src)]) == 0
    first = (src / "components" / "index.md").read_text()
    assert "index-written" in capsys.readouterr().err
    assert "stale overview" not in first

    assert gci.main(["--src", str(src)]) == 0
    assert (src / "components" / "index.md").read_text() == first
    assert "index-unchanged" in capsys.readouterr().err


@readable(
    intention="a missing components/ tree fails loudly with exit 1",
    steps=["run main against an src tree without components/", "check exit and stderr"],
    criteria=["exit 1", "components-missing event in stderr"],
)
def test_missing_components_tree_fails_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()

    assert gci.main(["--src", str(src)]) == 1
    assert "components-missing" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# real-tree freshness contract (the gate behind make check)
# ---------------------------------------------------------------------------


@readable(
    intention="the committed overview is exactly what render_index produces "
    "for the real tree -- stale overviews fail make check",
    steps=[
        "render the real doc/src tree",
        "compare against the committed src/components/index.md",
    ],
    criteria=["byte-identical output"],
)
def test_real_tree_render_equals_committed_index() -> None:
    rendered = gci.render_index(DOC / "src")
    committed = (DOC / "src" / "components" / "index.md").read_text()
    assert rendered == committed


@readable(
    intention="the committed overview lists every component page exactly once",
    steps=[
        "enumerate the real src/components/*.md pages (minus index)",
        "collect the overview's link targets",
    ],
    criteria=[
        "target set equals page set",
        "one bullet per page, no duplicates",
    ],
)
def test_real_tree_lists_every_component_page() -> None:
    md = (DOC / "src" / "components" / "index.md").read_text()
    targets = [
        ln.rsplit("(", 1)[1][:-1] for ln in md.splitlines() if ln.startswith("- ")
    ]
    pages = sorted(
        p.name
        for p in (DOC / "src" / "components").glob("*.md")
        if p.name != "index.md"
    )
    assert targets == pages


@readable(
    intention="the nav's Components group leads with the Overview entry "
    "pointing at the generated page",
    steps=[
        "parse the real zensical.toml nav",
        "check the Components section's first entry",
    ],
    criteria=["section[0] == {'Overview': 'components/index.md'}"],
)
def test_nav_components_group_leads_with_overview() -> None:
    nav = tomllib.loads((DOC / "zensical.toml").read_text())["project"]["nav"]

    assert components_section(nav)[0] == {"Overview": "components/index.md"}
