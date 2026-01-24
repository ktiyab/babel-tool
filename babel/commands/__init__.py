"""
Commands — Modular CLI command implementations with self-registration

Each command module:
1. Defines XxxCommand class (handler implementation)
2. Exports register_parser(subparsers) to configure its argparse
3. Exports handle(cli, args) to dispatch to handler methods

Registry pattern enables:
- Locality: Parser definition next to implementation
- Open/Closed: Add command = add module to COMMAND_MODULES
- Single Responsibility: Each module owns its full lifecycle
"""

import importlib
from typing import Dict, Callable, Any

from .base import BaseCommand

# Command modules that participate in auto-registration
# Order determines help display order
COMMAND_MODULES = [
    # Lifecycle
    'init_cmd',
    'capture',
    'why',
    'status',
    'check',
    'coherence',
    # Knowledge
    'review',
    'history',
    'list_cmd',
    # Validation
    'tensions',
    'validation',
    'questions',
    # Connections
    'link',
    'suggest_links',
    'gaps',
    # Maintenance
    'deprecate',
    'memo_cmd',
    'config_cmd',
    'git_cmd',
    # Tools
    'prompt',
    'map_cmd',
    'skill_cmd',
    'gather_cmd',
]

# Handler registry: command_name -> handle function
_handlers: Dict[str, Callable] = {}


def register_all(subparsers) -> None:
    """
    Discover and register all command parsers.

    Imports each module in COMMAND_MODULES and calls its register_parser()
    function if it exists. Also registers the handle() function for dispatch.

    Args:
        subparsers: argparse subparsers object from main parser
    """
    global _handlers
    _handlers.clear()

    for module_name in COMMAND_MODULES:
        try:
            module = importlib.import_module(f'.{module_name}', __package__)

            # Register parser if module provides it
            if hasattr(module, 'register_parser'):
                module.register_parser(subparsers)

            # Register handler if module provides it
            if hasattr(module, 'handle'):
                # Get command name from module (or derive from module name)
                cmd_name = getattr(module, 'COMMAND_NAME', None)
                if cmd_name is None:
                    # Derive from module name: 'capture' -> 'capture', 'init_cmd' -> 'init'
                    cmd_name = module_name.replace('_cmd', '')

                # Handle modules that register multiple commands
                cmd_names = getattr(module, 'COMMAND_NAMES', [cmd_name])
                for name in cmd_names:
                    _handlers[name] = module.handle

        except ImportError as e:
            # Log but don't fail - allows graceful degradation
            import sys
            print(f"Warning: Could not load command module '{module_name}': {e}", file=sys.stderr)


def dispatch(command: str, cli: Any, args: Any) -> Any:
    """
    Dispatch command to its registered handler.

    Args:
        command: Command name from args.command
        cli: IntentCLI instance
        args: Parsed argparse arguments

    Returns:
        Result from handler (if any)

    Raises:
        KeyError: If command not registered
    """
    if command not in _handlers:
        raise KeyError(f"Unknown command: {command}. Available: {list(_handlers.keys())}")

    return _handlers[command](cli, args)


def get_registered_commands() -> list:
    """Get list of registered command names."""
    return list(_handlers.keys())


__all__ = ['BaseCommand', 'register_all', 'dispatch', 'get_registered_commands']
