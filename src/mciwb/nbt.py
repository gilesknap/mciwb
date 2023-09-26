import json
import re

from mciwb.logging import log

# extract preamble from string responses to commands (benign for raw SNBT)
preamble_re = re.compile(r"[^\[{]*(.*)")
# extract list type identifiers
list_types_re = re.compile(r"[LBI];")
# regex to extract all unquoted items
unquoted_re = re.compile(r'([-.A-Za-z0-9]+)(?=([^"]*"[^"]*")*[^"]*$)')
# regex to extract numeric values
integers_re = re.compile(r'"(\d+)[bsl]?"')
no_decimal_floats_re = re.compile(r'"(-?[0-9]+)[fd]"')
floats_re = re.compile(r'"(-?\d+.\d+)[fd]"')


def parse_nbt(s_nbt_text: str) -> object:
    """
    Naive deserialization of an SNBT string into a object graph of Python types.

    Note that this is one way only since the following details are lost:
    - distinction between byte, short, int long, types (suffixes of b,s,none,l)
    - distinction between float, double types (suffixes of f,d)
    - distinction between SNBT and raw JSON (enclosed in single quotes)

    See https://minecraft.wiki/w/NBT_format
    """
    try:
        text = preamble_re.sub(r"\1", s_nbt_text)
        text = list_types_re.sub(r"", text)
        text = unquoted_re.sub(r'"\1"', text).replace("'", "")
        text = no_decimal_floats_re.sub(r"\1.0", text)
        text = floats_re.sub(r"\1", text)
        text = integers_re.sub(r"\1", text)
        text = text.replace('"true"', '"True"').replace('"false"', '"False"')

        return json.loads(text)
    except Exception as e:
        log.error(f"Error parsing NBT text: {s_nbt_text} \n\n ERROR: {e}")
        return None
