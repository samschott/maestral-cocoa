# -*- coding: utf-8 -*-

import sys
import argparse

from maestral.daemon import freeze_support


def main():
    """
    This is the main entry point for frozen executables.
    If only the --config-name option is given, it starts the GUI with the given config.
    If the --cli option is given, all following arguments will be passed to the CLI.
    If the --frozen-daemon option is given, an idle maestral daemon is started. This is to
    support launching the daemon from frozen executables as produced for instance by
    PyInstaller.
    """

    freeze_support()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("-c", "--config-name", default="maestral")
    parsed_args, remaining = parser.parse_known_args()

    if parsed_args.cli:
        import maestral.cli

        sys.argv[0] = "maestral"
        sys.argv.remove("--cli")
        maestral.cli.main()
    else:
        from maestral_cocoa.main import run

        run(parsed_args.config_name)
