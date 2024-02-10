"""
Implement exploding arrows.
"""

from mciwb.imports import (
    Direction,
    Item,
    Monitor,
    Vec3,
    get_client,
    parse_nbt,
    vec2params,
)

exploding = "exploding_arrows"
arrow_entity = "limit=1, type=arrow, nbt={inGround:1b}"


def enable_explosions(power=1):
    def explosion_test():
        c = get_client()
        result = c.data.get(entity=f"@e[{arrow_entity}]")

        if "Arrow has" in result:
            nbt = parse_nbt(result)
            pos = Vec3(*nbt["Pos"]).with_ints()  # type: ignore

            c.kill(f"@e[{arrow_entity}, {vec2params(pos)}]")
            for i in range(power):
                c.summon(str(Item.TNT), pos + Direction.UP * (i - power // 2))
                c.summon(str(Item.TNT), pos + Direction.EAST * (i - power // 2))
                c.summon(str(Item.TNT), pos + Direction.NORTH * (i - power // 2))

    Monitor.stop_named(exploding)
    Monitor(explosion_test, name=exploding)
