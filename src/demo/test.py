import threading
from time import sleep

from mcipc.rcon.je import Client

from mciwb.nbt import parse_nbt


def get_player_pos(name: str, wait: float):
    with Client("nuc2", port=30555, passwd="spider") as client:
        for i in range(100):
            x = client.data.get(entity="@p", path="Pos")
            print(name, parse_nbt(x))
            sleep(wait)


def get_player_pos2(name: str, wait: float):
    client = Client("nuc2", port=30555, passwd="spider")
    client.connect(True)
    for i in range(100):
        x = client.data.get(entity="@p", path="Pos")
        print(name, parse_nbt(x))
        sleep(wait)


client = Client("nuc2", port=30555, passwd="spider")
client.connect(True)


def get_player_pos3(name: str, wait: float):
    # share the connection between threads
    for i in range(100):
        x = client.data.get(entity="@p", path="Pos")
        print(name, parse_nbt(x))
        sleep(wait)


def go():
    test = get_player_pos2
    t1 = threading.Thread(target=test, args=("t1", 0.01))
    t2 = threading.Thread(target=test, args=("t2", 0.05))
    t1.start()
    t2.start()
