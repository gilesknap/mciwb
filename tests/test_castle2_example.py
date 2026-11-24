"""
Run the offline checks of examples/castle2 (which imports examples/castle),
so that a change that breaks the examples fails the unit tests: no server
is needed. The examples change sys.path and set defaults in os.environ when
they are imported, and their module names are short (``play``, ``people``,
``village``), so the checks run in a Python of their own.
"""

import os
import subprocess
import sys
from pathlib import Path

CASTLE2 = Path(__file__).parents[1] / "examples" / "castle2"
# the variables that move or resize the castle (castle_layout, castle2_layout)
SITE = ("ORIGIN", "SPAWN", "NAME", "BANNER", "BAILEY_DEPTH")
CHECKS = """
import build_castle2  # puts castle on sys.path; play and protect plan the bank
import castle2_layout
import cmdblocks
import house_rig

from mciwb.imports import Vec3

# castle's layout, the village and the command bank's box
assert castle2_layout.castle2_problems() == [], castle2_layout.castle2_problems()
# the bank as planned, with the reset's forceload order
assert len(cmdblocks.plan().blocks) > 100
assert cmdblocks.layout_problems() == [], cmdblocks.layout_problems()
# every variant of the house, as house_rig.py checks them offline
which = list(range(len(house_rig.VARIANTS)))
houses = house_rig.build_row(Vec3(0, 100, 0), which)
assert house_rig.report(houses, house_rig.VARIANTS)
"""


def test_castle2_offline_checks():
    env = {k: v for k, v in os.environ.items() if k not in SITE}
    result = subprocess.run(
        [sys.executable, "-c", CHECKS],
        cwd=CASTLE2,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
