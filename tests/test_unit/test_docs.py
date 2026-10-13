"""
Check that the code samples in the docs still match the API.

The tutorials and how-tos quote imports, demo functions and IPython output
that are easy to forget when the code changes, so check what can be checked
without a Minecraft server.
"""

import ast
import importlib
import re
from pathlib import Path

import pytest

from mciwb.imports import Item

docs = Path(__file__).parents[2] / "docs"
doc_files = sorted([*docs.glob("**/*.rst"), *docs.glob("**/*.md")])

# e.g. "from mciwb.imports import Direction, Item" in a code block
re_import = re.compile(r"^\s*from ((?:mciwb|buildings)[\w.]*) import ([\w, ]+)$", re.M)
# e.g. ".. literalinclude :: ../../src/mciwb/demo/pagoda.py" and its options
re_include = re.compile(r"^\.\. literalinclude ?:: (\S+)\n((?:[ \t]+:\w+:.*\n)*)", re.M)
# e.g. "Out[5]: <Item.SAND: 'minecraft:sand'>" in sample IPython output
re_item_repr = re.compile(r"<Item\.\w+: '[^']*'>")


def _docs_matching(regex: re.Pattern[str]) -> list[tuple[Path, re.Match[str]]]:
    return [
        (doc, match)
        for doc in doc_files
        for match in regex.finditer(doc.read_text(encoding="utf-8"))
    ]


def _id(doc: Path, match: re.Match[str]) -> str:
    return f"{doc.relative_to(docs)}:{match.group(0).strip().splitlines()[0]}"


imports = _docs_matching(re_import)
includes = _docs_matching(re_include)
item_reprs = _docs_matching(re_item_repr)


def test_docs_found():
    assert doc_files
    assert imports and includes and item_reprs


@pytest.mark.parametrize(
    "doc, match", imports, ids=[_id(doc, match) for doc, match in imports]
)
def test_doc_imports(doc: Path, match: re.Match[str]):
    """imports in the docs name modules and objects that exist"""
    module_name, names = match.groups()
    # the tutorials have the reader copy the demo modules into a package
    # called buildings
    module_name = re.sub(r"^buildings\b", "mciwb.demo", module_name)
    module = importlib.import_module(module_name)
    for name in names.split(","):
        assert hasattr(module, name.strip()), f"{module_name} has no {name}"


@pytest.mark.parametrize(
    "doc, match", includes, ids=[_id(doc, match) for doc, match in includes]
)
def test_doc_literalincludes(doc: Path, match: re.Match[str]):
    """included files, and the objects picked out of them, exist"""
    path = (doc.parent / match.group(1)).resolve()
    assert path.is_file()
    pyobject = re.search(r":pyobject: (\w+)", match.group(2))
    if pyobject:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.ClassDef)
        }
        assert pyobject.group(1) in defined


@pytest.mark.parametrize(
    "doc, match", item_reprs, ids=[_id(doc, match) for doc, match in item_reprs]
)
def test_doc_item_reprs(doc: Path, match: re.Match[str]):
    """sample IPython output shows Items as they are printed"""
    name = re.search(r"<Item\.(\w+):", match.group(0))
    assert name
    assert match.group(0) == repr(Item[name.group(1)])
