"""Public deployment entrypoint for gpbiometricspy Studio.

This root app intentionally imports the fail-closed synthetic demonstration.
Use ``studio/app.py`` for the full local or authenticated research-data Studio.
"""

from studio.public_demo import app

__all__ = ["app"]
