"""Directory-plugin shim for Hermes.

This lets the repository work both as:
- a drop-in ~/.hermes/plugins/doctorpack directory, and
- a pip package exposing hermes_agent.plugins entry point.
"""

from hermes_doctorpack import register

__all__ = ["register"]
