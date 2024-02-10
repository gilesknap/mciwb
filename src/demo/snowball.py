"""
Implement exploding snowballs.

Note the snowball disappears when it hits something so we need to monitor
all snowballs in flight and generate a BOOM at the last known position as
they disappear.
"""

from time import sleep

from mciwb.imports import Item, Monitor, Vec3, get_client, parse_nbt

exploding = "exploding_snowballs"


def enable_snowballs():
    Monitor.stop_named(exploding)
    Monitor(monitor_snowballs, name=exploding, poll_rate=0.1)


def uuid_str(nbt: dict):
    # need to parse uuid because of the I; and default str(list) has extraneous quotes
    # TODO replace parse_nbt with a class that handles all conversions
    uuid_str = (
        f"UUID:"
        f'[I; {nbt["UUID"][0]}, {nbt["UUID"][1]},'
        f' {nbt["UUID"][2]}, {nbt["UUID"][3]}]'
    )
    return uuid_str


def monitor_snowballs():
    c = get_client()
    # Note that snowballs have a default Air of 300 (on MC 1.19.2 anyway)
    result = c.data.get(entity="@e[limit=1, type=snowball, nbt={Air:300s}]")
    if "Snowball" in result:
        nbt = parse_nbt(result)
        if isinstance(nbt, dict):
            # change Air property so monitor_snowballs no longer sees this snowball
            entity = f"@e[limit=1, type=snowball, nbt={{{uuid_str(nbt)}}}]"
            c.data.merge(entity=entity, nbt="{Air:301}")

            Monitor(track_snowball, once=True, params=(entity, result))


def track_snowball(entity: str, result: str):
    c = get_client()

    # track for 20 secs only
    for _i in range(200):
        sleep(0.1)
        last_result = result
        result = c.data.get(entity=entity)
        if "Snowball" not in result:
            nbt = parse_nbt(last_result)
            if isinstance(nbt, dict):
                pos = Vec3(*nbt["Pos"]).with_ints()
                c.summon(str(Item.TNT), pos)
            break
