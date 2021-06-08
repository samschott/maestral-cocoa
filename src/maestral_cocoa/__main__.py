# -*- coding: utf-8 -*-

import sys
import argparse

from maestral.daemon import freeze_support as freeze_support_daemon


def main():
    """
    This is the main entry point. It starts the GUI with the given config.
    """

    from .app import run

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config-name", default="maestral")
    parsed_args, _ = parser.parse_known_args()

    run(parsed_args.config_name)


def freeze_support_cli():
    """
    Provides support to start the CLI from a frozen executable.
    """

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cli", action="store_true")
    parsed_args, remaining = parser.parse_known_args()

    if parsed_args.cli:
        from maestral.cli import main

        sys.argv = ["maestral"] + remaining
        main(prog_name="maestral")
        sys.exit()


if __name__ == "__main__":
    freeze_support_cli()
    freeze_support_daemon()
    main()
