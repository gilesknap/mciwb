from argparse import ArgumentParser

from . import __version__

__all__ = ["main"]


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("-v", "--version", action="version", version=__version__)
    args = parser.parse_args(args)


# test with: python -m mciwb
if __name__ == "__main__":
    main()
