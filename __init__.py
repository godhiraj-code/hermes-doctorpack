"""Directory-plugin shim for Hermes.

This lets the repository work both as:
- a drop-in ~/.hermes/plugins/doctorpack directory, and
- a pip package exposing hermes_agent.plugins entry point.
"""

# Choose the import context before importing so internal import failures are
# preserved, even if another copy of hermes_doctorpack is installed.
if __package__:
    from .hermes_doctorpack import register
else:  # Direct module loading, including pytest collection of this shim.
    from hermes_doctorpack import register

__all__ = ["register"]
