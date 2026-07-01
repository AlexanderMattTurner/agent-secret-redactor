# agent-secret-redactor-daemon

An optional long-lived daemon wrapping [`agent-secret-redactor`](../README.md).

The in-process API (`agent_secret_redactor.redact`) configures detect-secrets on
every call. For a hot path — a tool-output pipeline redacting many payloads per
session — that startup cost dominates. This daemon pays it **once** (configures
the plugin set and primes the mapping cache at startup), then serves each request
as just a scan over a Unix socket.

## Wire protocol

Both directions: a 4-byte big-endian unsigned length prefix, then that many bytes
of UTF-8 JSON.

- **Request:** `{"text": str, "map": bool, "web_ingress": bool, "env_secrets": {name: value}}`
- **Response:** the same object a one-shot `handle_request` returns —
  `{"text", "found"}` (plain), `{"text", "pairs", "found"}` or `{"unmappable"}`
  (map), JSON `null` when nothing was redacted, or `{"error"}` when the input
  could not be vetted (fail closed for that call only).

`env_secrets` is `name -> value` supplied **per request**: the socket may be
shared across sessions, so the daemon redacts the requester's values, not its own
environment.

## Run

```bash
agent-secret-redactor-daemon /path/to/redactor.sock
```

The socket is created `0600` under a `0700` directory, and its mere existence
means the daemon is ready (it binds only after priming). A crashed daemon leaves
a stale socket file that the next `serve` reclaims under a lock.
