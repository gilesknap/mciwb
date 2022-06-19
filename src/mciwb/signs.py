"""
Add an interactive capability through the placing of signs in the world
"""
import re
from typing import Dict

from mcwb import Vec3

from mciwb import Client, Item, Player
from mciwb.iwb import CallbackFunction

sign_text = re.compile(r"""Text1: '{"text":"([^"]*)"}'""")


class Sign:
    """
    Each sign object can be used to monitor the placing of signs by a single
    player. The object can be hooked to functions that are to be called when
    a sign is placed by the player.

    By default the Sign object is initialized with select/copy/paste
    functions
    """

    def __init__(self, player: Player):
        self.player = player
        self.signs: Dict[str, CallbackFunction] = {}
        self.client: Client

    def _calc_pos(self, x, y, z, player_relative):
        """
        TODO
        """
        offset = Vec3(x, y, z)
        if player_relative:
            pos = self.player.pos()
            return pos.with_ints() + offset
        else:
            return offset

    def _get_target_block(self, pos: Vec3, facing: Vec3):
        """
        determine the target block that the sign at pos indicates
        """
        # use 'execute if' with a benign command like seed
        result = self.client.execute.if_.block(pos, "minecraft:oak_wall_sign").run(
            "seed"
        )

        if "Seed" in result:
            # wall signs target the block behind them
            pos += facing
        else:
            # standing signs target the block below them
            pos += Vec3(0, -1, 0)

        return pos

    def _poll(self, client: Client):
        """
        check if a sign has been placed in front of the player
        1 to 4 blocks away and take action based on sign text
        """
        self.client = client

        facing = self.player.facing(client)
        for height in range(-1, 3):
            for distance in range(1, 4):
                pos = self.player.current_pos + facing * distance
                block_pos = pos.with_ints() + Vec3(0, height, 0)
                data = client.data.get(block=block_pos)
                match = sign_text.search(data)
                if match:
                    text = match.group(1)
                    target = self._get_target_block(block_pos, facing)
                    client.setblock(
                        block_pos,
                        Item.AIR,  # type: ignore
                    )
                    # TODO hook to action
                    print(text, target)

    def add_sign(self, name: str, function: CallbackFunction):
        self.signs[name] = function

    def remove_sign(self, name: str, function: CallbackFunction):
        del self.signs[name]
