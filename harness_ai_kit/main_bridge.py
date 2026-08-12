from __future__ import annotations

import sys
import types
from types import ModuleType


def export_core_symbols(target_globals: dict[str, object], core_module: ModuleType) -> None:
    for name in getattr(core_module, "__all__", ()):
        target_globals[name] = getattr(core_module, name)


class BridgedMainModule(types.ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        core_module = getattr(self, "_bridge_core", None)
        if core_module is not None and name != "_bridge_core" and hasattr(core_module, name):
            setattr(core_module, name, value)


def activate_main_bridge(module_name: str, target_globals: dict[str, object], core_module: ModuleType) -> None:
    export_core_symbols(target_globals, core_module)
    module = sys.modules[module_name]
    module.__class__ = BridgedMainModule
    setattr(module, "_bridge_core", core_module)
