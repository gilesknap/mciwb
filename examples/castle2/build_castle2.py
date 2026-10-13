"""
Build Castle 2, stage by stage::

    mciwb run build_castle2.py                           # everything
    STAGES=earthworks,bailey mciwb run build_castle2.py  # some stages

Castle 2 is Castle Fable (``examples/castle``, which must sit beside this
folder) with a bailey of depth 162: this driver runs castle's build
(``build_castle.main``) with castle2's layout and castle2's stages added to
castle's. The stages, the site's forceload, the player check and the
entity checks are castle's (see its README). The defaults (site, name,
banner) are in castle2_layout.DEFAULTS; the environment overrides them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import castle2_layout  # noqa: E402, I001  (first: it sets up castle's layout)
import build_castle  # noqa: E402

# castle's layout check, extended with castle2's
build_castle.layout_problems = castle2_layout.castle2_problems


def main() -> None:
    build_castle.main()


if __name__ == "__main__":
    main()
