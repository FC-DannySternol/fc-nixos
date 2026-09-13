"""Shared CLI plumbing for the docs pipeline tools.

The five CLI modules (:mod:`tools.checkout_versioned_docs`,
:mod:`tools.gen_platform_versions`,
:mod:`tools.gen_changes_index`, :mod:`tools.release_notes`,
:mod:`tools.scaffold_page`) share the same argparse defaults and the
same stderr logging contract:

* :data:`DOC_ROOT` / :data:`REPO_ROOT` -- doc/-relative path
  constants, resolved from THIS module (never the cwd), so every tool
  works from any directory (the Makefile runs them from doc/);

* :func:`configure_cli_logging` -- ONE structlog configuration
  (ISO timestamps, log level, ``ConsoleRenderer`` without colors)
  writing to stderr, resolved at call time: ``make`` surfaces a
  failing prerequisite's stderr verbatim while stdout stays clean
  for tool output (``--dry-run`` pages, zensical build input), and
  pytest's capsys captures it (capture_logs around ``main()`` does
  NOT work: the reconfiguration clobbers it).
"""

from __future__ import annotations

import sys
from pathlib import Path

import structlog

# doc/ root -- defaults resolve relative to the module, not the cwd, so
# the tools work from any directory (the Makefile runs them from doc/).
DOC_ROOT = Path(__file__).resolve().parents[1]

# The repository that carries the manual: doc/'s parent.
REPO_ROOT = DOC_ROOT.parent

# Minimum log level for the CLIs (matches logging.INFO; the int literal keeps
# the tools free of an ``import logging`` per the project's structlog-only rule).
INFO_LEVEL = 20


def configure_cli_logging() -> None:
    """Render human-readable diagnostics to stderr (see module docstring)."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(INFO_LEVEL),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
