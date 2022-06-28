"""
Add an interactive capability through the placing of signs in the world
"""
import logging
import re
from time import sleep
from typing import Dict

from mcwb.types import Item, Vec3

from mciwb.copier import CopyPaste
from mciwb.monitor import CallbackPosFunction
from mciwb.player import Player
from mciwb.threads import get_client


class Signs:
    """
    Each sign object can be used to monitor the placing of signs by a single
    player. The object can be hooked to functions that are to be called when
    a sign is placed by the player.

    By default each Sign object is initialized with select/copy/paste
    functions
    """

    re_sign_text = re.compile(r"""Text1: '{"text":"([^"]*)"}'""")
    re_sign_entity = (
        """minecraft:oak_sign{{BlockEntityTag:{{Text1:'{{"text":"{0}"}}'}},"""
        """display:{{Name:'{{"text":"{0}"}}'}}}}"""
    )

    wall_sign = "minecraft:oak_wall_sign"

    def __init__(self, player: Player):
        self.player = player
        self.copy = CopyPaste()
        self.signs: Dict[str, CallbackPosFunction] = self.copy.get_commands()

    def get_target_block(self, pos: Vec3, facing: Vec3) -> Vec3:
        """
        determine the target block that the sign at pos indicates
        """
        # use 'execute if' with a benign command like seed
        result = get_client().execute.if_.block(pos, self.wall_sign).run("seed")

        if "Seed" in result:
            # wall signs target the block behind them
            pos += facing
        else:
            # standing signs target the block below them
            pos += Vec3(0, -1, 0)

        return pos

    def poll(self):
        """
        check if a sign has been placed in front of the player
        1 to 4 blocks away and take action based on sign text
        """
        client = get_client()

        facing = self.player.facing
        player_pos = self.player.pos
        for height in range(-1, 3):
            for distance in range(1, 4):
                sleep(0)  # don't hog the connection
                pos = player_pos + facing * distance
                block_pos = pos.with_ints() + Vec3(0, height, 0)
                data = client.data.get(block=block_pos)
                match = self.re_sign_text.search(data)
                if match:
                    text = match.group(1)
                    logging.debug(f"Sign at {pos} has text {text}")
                    target = self.get_target_block(block_pos, facing)
                    client.setblock(
                        block_pos,
                        Item.AIR,  # type: ignore
                    )
                    self.do_action(text, target)

    def do_action(self, command: str, target: Vec3):
        # if the command is not found then this is just an ordinary sign (I assume!)
        if command in self.signs:
            logging.debug(f"Calling action for {command}")
            self.signs[command](target)

    def add_sign(self, name: str, function: CallbackPosFunction):
        self.signs[name] = function

    def remove_sign(self, name: str, function: CallbackPosFunction):
        del self.signs[name]

    def give_signs(self):
        """
        Give player one of each command sign in our commands list
        """
        client = get_client()
        for command in self.signs:
            client.give(self.player.name, self.re_sign_entity.format(command))
