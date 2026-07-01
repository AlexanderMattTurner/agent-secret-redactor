# agent-secret-redactor

An agent-agnostic secret-redaction engine. Plain text in, redacted text (or a
lossless **rehydration map**) out. It detects and removes API keys, tokens, PEM
private keys, and caller-configured environment-variable values from tool output
before a model ever sees them.

[detect-secrets](https://github.com/Yelp/detect-secrets) is the single detection
oracle, supplemented with custom detectors for formats it lacks (Anthropic,
Google, OpenRouter, GitHub fine-grained/classic, GitLab, Vault, Terraform,
DigitalOcean, Cloudflare, Groq, xAI, Replicate, full-JWT), a field-value regex
for `key = value` shapes, PEM-block collapse, cross-line reassembly of
newline-split tokens, and exact-match redaction of configured env-var values.

## Install

```bash
pip install agent-secret-redactor
```

The optional daemon (configure once, redact many, over a Unix socket) is a
separate package: `pip install agent-secret-redactor-daemon`.

## Usage

```python
from agent_secret_redactor import redact, redact_map, RedactorConfig

redact("key: AKIAIOSFODNN7EXAMPLE")
# ("key: [REDACTED: AWS Access Key]", ["AWS Access Key"])

# Redact the *value* of a configured env var by exact match:
config = RedactorConfig(provider_vars={"VENICE_INFERENCE_KEY": "…the-key…"})
redact("model said …the-key… verbatim", config)
# ("model said [REDACTED: VENICE_INFERENCE_KEY] verbatim", ["VENICE_INFERENCE_KEY"])
```

## Public contract

### `redact(text, config=None) -> (redacted_text, found_types)`

`found_types` lists each redacted detector's type in redaction order.

### `redact_map(text, config=None) -> {text, pairs, found}`

The **rehydration** differentiator — an injective, deterministic map back to the
original bytes. Each entry of `pairs` is:

```json
{ "placeholder": "[REDACTED: …]", "original": "<exact original bytes>", "start": 42 }
```

`start` is the offset of the placeholder in `text`. Substituting every `original`
at its `start` reconstructs the input **byte-for-byte** — a downstream layer (e.g.
[`agent-input-sanitizer`](https://github.com/alexander-turner/agent-input-sanitizer)'s
`rehydrate`) can translate any span of the redacted view back to disk losslessly.
The `{placeholder, original, start}` schema is a **two-way contract** with that
consumer; it is not redefined here.

If `text` already contains the reserved private-use sentinels the map machinery
uses, `redact_map` returns `{"unmappable": <reason>}` (fail closed).

> One acknowledged limitation: when a long non-detected run is glued with **no
> separator** directly onto a detected secret, the field-value regex can swallow a
> map sentinel and the view will not round-trip. The consumer detects the mismatch
> and fails closed. Realistic (separated) inputs round-trip exactly.

### Configuration is passed in, never discovered — `RedactorConfig`

| field | meaning |
| --- | --- |
| `provider_vars` / `host_cred_vars` | `name -> value` maps whose values are redacted by exact match (labelled `[REDACTED: <name>]`). Unioned, provider first. |
| `invisible_charset` | Payload-capable invisible code points to strip / tolerate. `None` (default) sources the **shared** set from `agent-input-sanitizer` — see below. |
| `web_ingress` | Mark attacker-controlled text (disables the name-based benign-skip heuristics). |
| `high_confidence` | Structural detectors only (drop the fuzzy keyword / field-value matchers). |
| `min_secret_len` | Floor below which a configured value is treated as a placeholder (default 16). |

The engine reads no config files and scans no environment. The **caller** supplies
the env-var set — which for claude-guard is the union of `monitor-providers.json`
and `scrubbed-env-vars.json`, a security SSOT shared with the monitor and sandbox.
A caller building that set from those files must fail closed (hard read) if either
is missing, never silently under-match.

## Shared invisible-character charset

The invisible charset the redactor strips (before detection) and tolerates spliced
inside env-bound keys **must equal** `agent-input-sanitizer`'s deletion set — or a
key spliced with a code point one side omits escapes both layers. So it is **not**
defined here: it is imported from that package's shared SSOT
(`agent_input_sanitizer.invisible.invisible_charset`). There is deliberately no
local copy and no fallback — if the shared dependency is unavailable, charset
resolution **raises** (fail closed) rather than under-matching with a partial set.

## In-process vs. daemon

`redact` / `redact_map` configure the detect-secrets plugin set on every call
(the mapping cache is process-global; a per-call clear keeps an unrelated scan
from leaving the wrong plugins primed). For a hot path, either hold a
`configure_plugins()` block open and call `redact_configured(...)`, or use the
daemon package.

## License

Apache-2.0.
