from importlib.metadata import version

__version__ = version("mciwb")
del version

__all__ = ["__version__"]
