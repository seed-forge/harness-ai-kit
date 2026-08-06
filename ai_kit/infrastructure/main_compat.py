from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any


def load_main_globals(module_globals: dict[str, Any], protected_names: set[str]) -> None:
    from .. import main as main_module

    for name, value in vars(main_module).items():
        if name not in protected_names and not name.startswith("__"):
            module_globals[name] = value


def bridged_main_function(module_globals: dict[str, Any], protected_names: set[str]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            load_main_globals(module_globals, protected_names)
            return func(*args, **kwargs)

        return wrapper

    return decorator
