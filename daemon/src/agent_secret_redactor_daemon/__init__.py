"""Optional Unix-socket daemon wrapping the agent-secret-redactor core.

Consumers pick in-process (:func:`agent_secret_redactor.redact`) or, for a hot
path that would otherwise pay the detect-secrets startup cost per call, this
daemon — which configures the plugin set once and serves each request as a scan.
"""

from .server import FRAME_CAP, serve

__all__ = ["serve", "FRAME_CAP"]

__version__ = "0.1.0"
