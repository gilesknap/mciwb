"""
Add an interactive capability through the placing of command signs in the world
"""

import re
from collections.abc import Callable
from time import sleep

from mcwb.types import Item, Vec3

from mciwb.copier import CopyPaste
from mciwb.logging import log
from mciwb.player import Player
from mciwb.threads import get_client

CallbackPosFunction = Callable[[Vec3], None]


class Signs:
    """
    Monitor the world for signs placed by a player. Perform an action based
    on the text of the sign.

    Each sign object can be used to monitor the placing of signs by a single
    player. The object can be hooked to functions that are to be called when
    a sign is placed by the player.

    By default each Sign object is initialized with select/copy/paste
    functions. Additional signs with callback functions can be added.

    For best results, use the bound methods of an object for the callback
    functions. That way the user code can manage state within the object
    providing those functions.
    """

    _re_sign_text = re.compile("""front_text.*messages: \\['"([^"]*)"',""")
    _re_sign_entity = (
        """minecraft:oak_sign["""
        """block_entity_data={{"""
        """id:oak_sign,front_text:{{"""
        """messages:['["{0}"]','[""]','[""]','[""]']"""
        """}}"""
        """}},"""
        """minecraft:item_name="{0}"]"""
    )

    _wall_sign = "minecraft:oak_wall_sign"

    def __init__(self, player: Player):
        self.player = player
        self.copy = CopyPaste()
        self.signs: dict[str, CallbackPosFunction] = self.copy.get_commands()

    def _get_target_block(self, pos: Vec3, facing: Vec3) -> Vec3:
        """
        determine the target block that the sign at pos indicates
        """
        # use 'execute if' with a benign command like seed
        result = get_client().execute.if_.block(pos, self._wall_sign).run("seed")

        if "Seed" in result:
            # wall signs target the block behind them
            pos += facing
        else:
            # standing signs target the block below them
            pos += Vec3(0, -1, 0)

        return pos

    def _poll(self):
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
                match = self._re_sign_text.search(data)
                if match:
                    text = match.group(1)
                    log.debug(f"Sign at {pos} has text {text}")
                    target = self._get_target_block(block_pos, facing)
                    self.do_action(text, target, block_pos)

    def do_action(self, command: str, target: Vec3, block_pos: Vec3):
        """
        Perform an action based on the text of the sign. The action is to
        call the callback function that is configured for this sign text.

        :param command: the text of the sign
        :param target: the target block that the sign indicates
        :param block_pos: the position of the block that the sign is on - this is
            cleared if the sign is used
        """
        # if the command is not found then this is just an ordinary sign (I assume!)
        if command in self.signs:
            get_client().setblock(block_pos, str(Item.AIR))
            log.info(f"{command} at {target}")
            self.signs[command](target)

    def add_sign(self, name: str, function: CallbackPosFunction):
        """
        Add a new sign type with its action callback function

        :param name: the text of the sign
        :param function: the callback function to be called when the sign is placed
        """
        # don't allow multiple signs with the same name
        self.remove_sign(name)
        self.signs[name] = function

    def remove_sign(self, name: str):
        """
        Stop monitoring for a sign with the given name

        :param name: the text of the sign
        """
        if name in self.signs:
            del self.signs[name]

    _sign_match = '{{"text":"{}"}}'

    def give_signs(self):
        """
        Give player one of each command sign in our commands list

        Check first if the player has the sign already
        """
        client = get_client()
        inventory = self.player.inventory
        for command in self.signs:
            if self._sign_match.format(command) not in inventory:
                client.give(self.player.name, self._re_sign_entity.format(command))
