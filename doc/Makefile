.PHONY: all html feeds serve clean test lint typecheck check

all: checkout-versioned-docs gen-platform-versions html feeds

# Explicit matched-rev override for the tools (empty: auto-detect --
# hg ACTIVE bookmark; git GITHUB_REF_NAME, then checked-out branch).
TOOL_ARGS := $(if $(MATCHED),--matched $(MATCHED),)

gen-platform-versions: 
	./appenv python -m tools.gen_platform_versions $(TOOL_ARGS)

checkout-versioned-docs: 
	./appenv python -m tools.checkout_versioned_docs $(TOOL_ARGS)

html:
	./zensical build

# Release-notes RSS feed (zensical-feeds companion CLI -- zensical has
# no plugin API yet). Runs AFTER html: the feed lands in _build/ next
# to the HTML, so CI's artifact upload ships it automatically.
feeds:
	./zensical-feeds

serve: checkout-versioned-docs gen-platform-versions
	./zensical serve

VERSIONED_DIRS := 25.11 26.05

clean:
	rm -rf _build $(VERSIONED_DIRS:%=src/%)
	rm -f src/.checkout-manifest.json

# The doc tests (tests/) need the dev dependency group: appenv builds
# the plain runtime venv (no pytest), so this goes through uv, which
# creates/syncs doc/.venv from pyproject.toml + uv.lock first.
test:
	uv run pytest tests

# Dev-only quality gates (same uv venv as test): ruff lint and the ty
# type checker over tools/ and tests/.
lint:
	uv run ruff check tools tests

typecheck:
	uv run ty check tools tests

# Full quality gate: lint + types + tests (what CI enforces).
check: lint typecheck test
