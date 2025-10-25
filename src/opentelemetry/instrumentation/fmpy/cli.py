"""CLI for OpenTelemetry FMPy instrumentation."""

import argparse
import sys
from typing import Optional, Sequence

from opentelemetry.instrumentation.fmpy import FmpyInstrumentor


def instrument_command(args: argparse.Namespace) -> int:
    """Handle the instrument command."""
    try:
        instrumentor = FmpyInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
            print("FMPy instrumentation enabled.")
        else:
            print("FMPy is already instrumented.")
        return 0
    except Exception as e:
        print(f"Error instrumenting FMPy: {e}", file=sys.stderr)
        return 1


def uninstrument_command(args: argparse.Namespace) -> int:
    """Handle the uninstrument command."""
    try:
        instrumentor = FmpyInstrumentor()
        if instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.uninstrument()
            print("FMPy instrumentation disabled.")
        else:
            print("FMPy is not currently instrumented.")
        return 0
    except Exception as e:
        print(f"Error uninstrumenting FMPy: {e}", file=sys.stderr)
        return 1


def status_command(args: argparse.Namespace) -> int:
    """Handle the status command."""
    try:
        instrumentor = FmpyInstrumentor()
        status = "enabled" if instrumentor.is_instrumented_by_opentelemetry else "disabled"
        print(f"FMPy instrumentation is {status}.")
        return 0
    except Exception as e:
        print(f"Error checking instrumentation status: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="opentelemetry-instrument-fmpy",
        description="OpenTelemetry FMPy instrumentation CLI",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Instrument command
    subparsers.add_parser(
        "instrument",
        help="Enable FMPy instrumentation"
    )

    # Uninstrument command
    subparsers.add_parser(
        "uninstrument",
        help="Disable FMPy instrumentation"
    )

    # Status command
    subparsers.add_parser(
        "status",
        help="Check instrumentation status"
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    command_map = {
        "instrument": instrument_command,
        "uninstrument": uninstrument_command,
        "status": status_command,
    }

    return command_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main())