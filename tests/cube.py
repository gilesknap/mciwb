from mcipc.rcon.item import Item
from mcipc.rcon.je import Client
from mcwb import Blocks, Volume
from mcwb.itemlists import grab
from mcwb.types import Anchor3, Cuboid, Vec3


class TestCube:
    def __init__(self, client: Client) -> None:
        self.client = client

        blue_row = [Item.BLUE_CONCRETE, Item.BLUE_CONCRETE, Item.BLUE_CONCRETE]
        red_row = [Item.RED_CONCRETE, Item.RED_CONCRETE, Item.RED_CONCRETE]
        hollow_row = [Item.RED_CONCRETE, Item.AIR, Item.RED_CONCRETE]
        top_profile = [blue_row, red_row, red_row]
        middle_profile = [blue_row, hollow_row, red_row]
        bottom_profile = [blue_row, blue_row, red_row]
        self.cube: Cuboid = [top_profile, middle_profile, bottom_profile]
        self.size = Vec3(2, 2, 2)
        # TODO does Volume's use of size need review?
        self.volume_size = Vec3(3, 3, 3)

        self.air = (((Item.AIR,) * 3) * 3) * 3

    def create(self, pos: Vec3, anchor: Anchor3 = Anchor3.BOTTOM_NW):
        """
        create a set of blocks in the world at pos
        """
        Blocks(self.client, pos, self.cube, anchor)

    def test(self, pos: Vec3, anchor: Anchor3 = Anchor3.BOTTOM_NW):
        """
        test that the test cube blocks exist at pos
        """
        dest_vol = Volume.from_anchor(pos, self.volume_size, anchor)
        dest_cuboid = grab(self.client, dest_vol)

        return dest_cuboid == self.cube

    def clear(self, pos: Vec3, anchor: Anchor3 = Anchor3.BOTTOM_NW):
        """
        clear blocks at location
        """
        volume = Volume.from_anchor(pos, self.volume_size, anchor)
        volume.fill(self.client, Item.AIR)