from __future__ import annotations

import argparse
from collections.abc import Callable

CommandHandler = Callable[[argparse.Namespace], int]


class CommandRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command: str, handler: CommandHandler) -> None:
        self._handlers[command] = handler

    def register_many(self, commands: set[str], handler: CommandHandler) -> None:
        for command in commands:
            self.register(command, handler)

    def dispatch(self, args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
        command = str(getattr(args, "command", ""))
        handler = self._handlers.get(command)
        if handler is None:
            parser.error(f"Unsupported command: {command}")
            return 2
        return handler(args)

