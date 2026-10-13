"""
Castle 2: Castle Fable (``examples/castle``) with a lower bailey twice as
deep, filled with a village. Import this module before any of castle's: it
sets castle2's defaults in the environment (the bailey's depth, the site,
the name and the banner colour), puts ``examples/castle`` on the import
path, and then re-exports everything in ``castle_layout``, so that castle's
modules and castle2's see the same layout::

    import castle2_layout  # first
    import build_inner     # castle's, laid out for castle2

Local coordinates are castle's (see castle_layout): x east, y up from the
bailey's standing level, z south from the upper ward's north wall. With
BAILEY_DEPTH=162 the bailey is x 0..120, z 65..226 and the gate is at
z 218..226.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
CASTLE = HERE.parent / "castle"
for folder in (HERE, CASTLE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

# castle2's defaults: the site surveyed at x 550..700, z -200..70 (flat and
# dry, ground 62..72, higher in the north-west), a name and a banner colour
# no other castle in the world uses (Fable red, the one at 148,-262 purple,
# the one at -300,-40 yellow)
DEFAULTS = {
    "BAILEY_DEPTH": "162",
    "ORIGIN": "560,68,-190",
    "SPAWN": "32,74,-64",
    "NAME": "Fable II",
    "BANNER": "cyan",
}
for _key, _value in DEFAULTS.items():
    os.environ.setdefault(_key, _value)

_early = sys.modules.get("castle_layout")
if _early is not None and str(_early.LD) != os.environ["BAILEY_DEPTH"]:
    raise SystemExit("import castle2_layout before castle's modules")

from castle_layout import *  # noqa: E402, F403
from castle_layout import LD, UD, ZS, layout_problems  # noqa: E402

# ---- the bailey's three parts, north to south (local z)
NORTH = (UD, UD + 55)  # barracks, stables, smithy, well and the cross paths
VILLAGE = (UD + 55, ZS - 36)  # the village round its market square
SOUTH = (ZS - 36, ZS)  # pens and paddocks, the market stalls by the gate


def castle2_problems() -> list[str]:
    """castle's layout check, plus castle2's own (houses, pens and lanes
    come in later phases)"""
    problems = layout_problems()
    if LD != 162:
        problems.append(f"castle2 is laid out for BAILEY_DEPTH=162, not {LD}")
    return problems
