"""Environment records, platform detection, and requirements analysis.

Re-exports from doctor_checks where the functions are co-located with
other diagnostic helpers.
"""
from harness_ai_kit.domain.doctor_checks import (
    current_platform_tags,
    environment_records_for_lockfile,
    environment_requirements_for_records,
    missing_environment_requirements,
)

__all__ = [
    "current_platform_tags",
    "environment_records_for_lockfile",
    "environment_requirements_for_records",
    "missing_environment_requirements",
]
