# -*- coding: utf-8 -*-

from maestral.daemon import freeze_support


def main():
    """
    This is the main entry point for frozen executables.
    If only the --config-name option is given, it starts the GUI with the given config.
    """

    import argparse
    from .app import run

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config-name", default="maestral")
    parsed_args, _ = parser.parse_known_args()

    run(parsed_args.config_name)


if __name__ == "__main__":
    freeze_support()
    main()
