from __future__ import annotations

import json
import subprocess

from pydantic import ValidationError

from .. import package_manager as pm

HANDLED_COMMAND_EXCEPTIONS = (
    FileExistsError,
    FileNotFoundError,
    KeyError,
    json.JSONDecodeError,
    subprocess.CalledProcessError,
    ValidationError,
    ValueError,
    RuntimeError,
)


def command_error_message(exc: BaseException) -> str:
    if isinstance(exc, ValidationError):
        return pm.manifest_validation_error(exc)
    return str(exc)
