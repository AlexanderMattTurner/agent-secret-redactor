"""Shared fixtures/helpers for the agent-secret-redactor test suite.

The original claude-guard tests drove ``main()`` over stdin/stdout and read
secret values from ``os.environ``. The library takes config *in*, so these
helpers call the public API directly: ``run_plain`` mirrors the old
``run_main`` (returns ``None`` when nothing is emitted), ``run_map`` mirrors the
old map-mode driver, and ``cfg`` builds a :class:`RedactorConfig`. No env
clearing is needed — a bare config has no env-bound values.
"""

import json
from pathlib import Path

import pytest

from agent_secret_redactor import RedactorConfig, handle_request, redact_map

SAMPLES_FILE = Path(__file__).resolve().parent / "secret-format-samples.json"
SAMPLES = json.loads(SAMPLES_FILE.read_text())["samples"]


def cfg(**kwargs) -> RedactorConfig:
    """A RedactorConfig with the given overrides (bare by default)."""
    return RedactorConfig(**kwargs)


def run_plain(text: str, config: RedactorConfig | None = None) -> dict | None:
    """Plain-mode redaction as a JSON-shaped dict, or ``None`` when nothing is
    emitted (clean input) — the ``run_main`` stand-in."""
    return handle_request(text, False, config or RedactorConfig())


def run_map(text: str, config: RedactorConfig | None = None) -> dict:
    """Map-mode redaction (always returns a dict)."""
    return redact_map(text, config or RedactorConfig())


def reconstruct(view: dict) -> str:
    """Substitute each pair's original at its placeholder offset in the view —
    the rehydration contract."""
    out, last = [], 0
    for p in view["pairs"]:
        out.append(view["text"][last : p["start"]])
        out.append(p["original"])
        last = p["start"] + len(p["placeholder"])
    out.append(view["text"][last:])
    return "".join(out)


@pytest.fixture
def eng():
    """The engine module (private helpers live here)."""
    import agent_secret_redactor.engine as engine

    return engine
