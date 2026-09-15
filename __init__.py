"""Directory-plugin shim for Hermes.

This lets the repository work both as:
- a drop-in ~/.hermes/plugins/doctorpack directory, and
- a pip package exposing hermes_agent.plugins entry point.
"""

try:
    # Directory install: Hermes imports this __init__.py as a package rooted at
    # the plugin dir, so the sub-package must be resolved relative to it.
    from .hermes_doctorpack import register
except ImportError:
    from hermes_doctorpack import register

__all__ = ["register"]
