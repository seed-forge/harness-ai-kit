from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .dispatch import CommandRouter

ConfigPathHandler = Callable[[argparse.Namespace, Path], int]
PlainHandler = Callable[[argparse.Namespace], int]


def register_command_routes(
    router: CommandRouter,
    *,
    config_path: Path,
    config_path_handlers: Mapping[str, ConfigPathHandler],
    plain_handlers: Mapping[str, PlainHandler],
    config_path_alias_handlers: Sequence[tuple[set[str], ConfigPathHandler]] = (),
) -> None:
    for command, handler in config_path_handlers.items():
        router.register(command, lambda args, handler=handler: handler(args, config_path))
    for command, handler in plain_handlers.items():
        router.register(command, handler)
    for commands, handler in config_path_alias_handlers:
        router.register_many(commands, lambda args, handler=handler: handler(args, config_path))

