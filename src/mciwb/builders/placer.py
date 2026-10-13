"""
`Placer` sends ``setblock`` and ``fill`` commands for the builders, checks
the server's responses and records the bounding box of what it changed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from mcipc.rcon.enumerations import FillMode
from mcwb import Vec3, Volume

from mciwb.builders.blockstate import Block, BlockState
from mciwb.logging import log
from mciwb.threads import Client, get_client

__all__ = ["BuildError", "Placer"]

# server responses that mean the command worked, or had nothing to change
_OK = (
    "Changed the block",
    "Could not set the block",
    "Successfully filled",
    "No blocks were filled",
)


# the most blocks one fill command may change (the server's default limit)
MAX_FILL = 32768


class BuildError(RuntimeError):
    """The server rejected a building command, e.g. an unknown block or
    a position that is not loaded"""


def _ints(pos: Vec3) -> Vec3:
    return Vec3(*pos).with_ints()


class Placer:
    """
    Place blocks with the RCON client of the current thread, recording the
    bounding box of every block placed.

    :param client: the client to use, defaults to ``get_client``
    """

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_client()
        self._lo: Vec3 | None = None
        self._hi: Vec3 | None = None

    @property
    def volume(self) -> Volume:
        """
        The bounding box of every block placed so far

        :raises ValueError: if nothing has been placed
        """
        if self._lo is None or self._hi is None:
            raise ValueError("nothing has been placed")
        return Volume.from_corners(self._lo, self._hi)

    def include(self, start: Vec3, end: Vec3 | None = None) -> None:
        """Extend the bounding box to include a block, or a box of blocks"""
        end = start if end is None else end
        lo = Vec3(*(min(a, b) for a, b in zip(start, end, strict=True)))
        hi = Vec3(*(max(a, b) for a, b in zip(start, end, strict=True)))
        if self._lo is None or self._hi is None:
            self._lo, self._hi = lo, hi
        else:
            self._lo = Vec3(*(min(a, b) for a, b in zip(self._lo, lo, strict=True)))
            self._hi = Vec3(*(max(a, b) for a, b in zip(self._hi, hi, strict=True)))

    def _check(self, command: str, result: str) -> str:
        log.debug(f"{command}: {result}")
        if not result.startswith(_OK):
            raise BuildError(f"{command} failed: {result}")
        return result

    def setblock(self, pos: Vec3, block: Block) -> str:
        """
        Set one block, e.g. ``placer.setblock(pos, "oak_stairs[half=top]")``.
        The block may carry block entity data, e.g. a sign's text::

            text = '''{front_text:{messages:['"Hi"','""','""','""']}}'''
            placer.setblock(pos, "oak_sign[rotation=4]" + text)
        """
        pos = _ints(pos)
        state = str(BlockState.parse(block))
        self.include(pos)
        return self._check(f"setblock {pos} {state}", self.client.setblock(pos, state))

    def fill(
        self,
        start: Vec3,
        end: Vec3,
        block: Block,
        mode: FillMode | None = None,
        filter: str | None = None,
    ) -> str:
        """
        Fill the box between two opposite corners, inclusive. Block entity
        data in *block* (``chest{Items:[...]}``) is given to every block.

        :param mode: e.g. ``FillMode.KEEP`` to only replace air
        :param filter: only replace these blocks, e.g. ``"minecraft:stone"``
            or a tag like ``"#minecraft:logs"``. Implies ``FillMode.REPLACE``
        :raises ValueError: if a filter is given with a mode other than REPLACE
        """
        if filter is not None:
            if mode not in (None, FillMode.REPLACE):
                raise ValueError(f"a fill filter needs FillMode.REPLACE, not {mode}")
            mode = FillMode.REPLACE
        start, end = _ints(start), _ints(end)
        state = str(BlockState.parse(block))
        size = Volume.from_corners(start, end).size
        if size.volume > MAX_FILL:
            # split the box in two across its longest side
            axis = max(range(3), key=lambda i: size[i])
            lo, hi = Vec3(*map(min, start, end)), Vec3(*map(max, start, end))
            middle = lo[axis] + size[axis] // 2
            first_end = Vec3(*(middle - 1 if i == axis else hi[i] for i in range(3)))
            second = Vec3(*(middle if i == axis else lo[i] for i in range(3)))
            self.fill(lo, first_end, state, mode, filter)
            return self.fill(second, hi, state, mode, filter)

        self.include(start, end)
        if mode is None:
            result = self.client.fill(start, end, state)
        else:
            result = self.client.fill(start, end, state, mode=mode, filter=filter)
        return self._check(f"fill {start} {end} {state}", result)

    def layer(self, y: int, cells: Mapping[tuple[int, int], Block]):
        """
        Place one horizontal layer of blocks at height *y*, given as a mapping
        of ``(x, z)`` to block. Uses one ``fill`` for each rectangle of the
        same block.
        """
        by_state: dict[str, list[tuple[int, int]]] = {}
        for (x, z), block in cells.items():
            by_state.setdefault(str(BlockState.parse(block)), []).append((x, z))

        for state, positions in by_state.items():
            for x1, z1, x2, z2 in rectangles(positions):
                if (x1, z1) == (x2, z2):
                    self.setblock(Vec3(x1, y, z1), state)
                else:
                    self.fill(Vec3(x1, y, z1), Vec3(x2, y, z2), state)


def rectangles(cells: Iterable[tuple[int, int]]) -> list[tuple[int, int, int, int]]:
    """
    Cover a set of ``(a, b)`` grid cells with rectangles ``(a1, b1, a2, b2)``
    (inclusive). Joins runs along *a*, then stacks runs that span the same
    *a* in consecutive rows of *b*. Tries both axes and returns the shorter
    list.
    """
    cell_set = set(cells)

    def cover(swap: bool) -> list[tuple[int, int, int, int]]:
        rows: dict[int, list[int]] = {}
        for a, b in cell_set:
            if swap:
                a, b = b, a
            rows.setdefault(b, []).append(a)
        # runs along a in each row, as (a1, a2) keyed by row b
        runs: dict[int, list[tuple[int, int]]] = {}
        for b, values in rows.items():
            values.sort()
            start = prev = values[0]
            for a in values[1:] + [None]:
                if a is None or a != prev + 1:
                    runs.setdefault(b, []).append((start, prev))
                    if a is not None:
                        start = a
                if a is not None:
                    prev = a
        # stack identical runs in consecutive rows
        open_rects: dict[tuple[int, int], int] = {}  # (a1, a2) -> first row
        result = []
        for b in sorted(runs):
            current = set(runs[b])
            for span in list(open_rects):
                if span not in current or b - 1 not in runs:
                    result.append((span[0], open_rects.pop(span), span[1], b - 1))
            for span in current:
                open_rects.setdefault(span, b)
            # close spans in this row that will not continue
            if b + 1 not in runs:
                for span in list(open_rects):
                    result.append((span[0], open_rects.pop(span), span[1], b))
        if swap:
            result = [(b1, a1, b2, a2) for a1, b1, a2, b2 in result]
        return result

    if not cell_set:
        return []
    return min(cover(False), cover(True), key=len)
