"""Environment manager: install environment requirements.

Re-exports from doctor_checks where the install function is co-located
with the diagnostic helpers that identify missing requirements.
"""
from harness_ai_kit.domain.doctor_checks import install_environment_requirements

__all__ = [
    "install_environment_requirements",
]
