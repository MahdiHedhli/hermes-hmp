"""Hermes Mobile Protocol (HMP) v1 server plugin.

Closed surface (HMP v1 PR-2, FR-054, constitution I). `register(ctx)` makes exactly two
registrations: the `hmp` platform adapter and the `hermes hmp` operator CLI. There are no hooks,
tools, slash commands, prompt sections or other `PluginContext` calls, here or anywhere else in the
package. `tools/ci/check_plugin_surface.py` enforces this by AST scan.

Importing this package imports no Hermes module. The adapter module, which subclasses Hermes's
documented `BasePlatformAdapter`, is imported only when the gateway builds the adapter.
"""

from __future__ import annotations

from typing import Any

from . import cli, compat
from .contract import CLI_COMMAND, PLATFORM_NAME

PLATFORM_LABEL = "Hermes Mobile (HMP)"
INSTALL_HINT = "Pair a phone with: hermes hmp pair offer"
CLI_HELP = "Hermes Mobile (HMP) operator commands"
CLI_DESCRIPTION = "Pair and manage Hermes Bot Mobile devices for this Hermes instance."


def _adapter_factory(config: Any) -> Any:
    """`adapter_factory(PlatformConfig) -> BasePlatformAdapter` (Hermes `register_platform`)."""
    from .adapter import HmpAdapter

    return HmpAdapter(config)


def register(ctx: Any) -> None:
    """Hermes plugin entry point. Exactly two registrations; never add a third."""
    ctx.register_platform(
        name=PLATFORM_NAME,
        label=PLATFORM_LABEL,
        adapter_factory=_adapter_factory,
        check_fn=compat.runtime_dependencies_present,
        install_hint=INSTALL_HINT,
    )
    ctx.register_cli_command(
        name=CLI_COMMAND,
        help=CLI_HELP,
        setup_fn=cli.setup_parser,
        handler_fn=cli.dispatch,
        description=CLI_DESCRIPTION,
    )
