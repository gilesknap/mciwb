"""
Functions for launching and controlling a Minecraft server in a Docker container.
"""
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir

from docker import from_env
from docker.models.containers import Container
from mcwb.types import Vec3

KEEP_SERVER = "MCIWB_KEEP_SERVER" in os.environ

HOST = "localhost"
SERVER_PORT = 20400
RCON_PORT = 20401
RCON_P = "pass"
ENTITY_NAME = "george"
ENTITY_POS = Vec3(0, -60, 0)

# the locally mapped temporary folder for minecraft data

data_folder = Path(gettempdir()) / "test_mc_servers"


class MinecraftServer:
    def __init__(self, name: str, rcon: int) -> None:
        self.rcon = rcon
        self.name = name
        self.folder = data_folder / name
        self.cont = self.minecraft_create()
        self.wait_server()

    def wait_server(self):
        """
        Wait until the server is ready to accept rcon connections

        Multiple calls to this with container restarts require passing a count.
        This is how many times the wait code looks for the server to come online
        in the logs.

        This is required because the --since argument to the docker logs command
        fails to return any logs at all.
        """

        start_time: datetime = datetime.now()
        timeout = 100

        self.cont.reload()
        if self.cont.status != "running":
            logs = "\n".join(str(self.cont.logs()).split(r"\n"))
            raise RuntimeError(f"minecraft server failed to start\n\n{logs}")

        logging.debug("waiting for mc server to come online")
        for block in self.cont.logs(stream=True):
            logging.debug(block.decode("utf-8").strip())
            if b"RCON running" in block:
                break
            elapsed = datetime.now() - start_time
            if elapsed.total_seconds() > timeout:
                raise RuntimeError("Timeout Starting minecraft")
        logging.debug("mc server is online")

    def minecraft_remove(self):
        """
        Remove a minecraft server container
        """
        # set env var MCIWB_KEEP_SERVER to keep server alive for faster
        # repeated tests and viewing the world with a minecraft client
        if self.cont and not KEEP_SERVER:
            logging.info("\nClosing the Minecraft Server ...")
            self.cont.stop()
            self.cont.remove()

    def minecraft_create(self) -> Container:
        """
        Spin up a test minecraft server and return a container object

        This fixture is run once per session, meaning that it does not need
        to be executed twice for two runs of the tests. This requires
        caution as the world must be reset to a known state.
        """

        # create and launch minecraft container once per session
        docker_client = from_env()

        for container in docker_client.containers.list(all=True):
            assert isinstance(container, Container)
            if container.name == self.name:
                if container.status == "running":
                    logging.info(f"test minecraft server '{self.name}' already running")
                    return container
                else:
                    container.remove()
                    break

        env = {
            "EULA": "TRUE",
            # "VERSION": "1.17.1",
            "SERVER_PORT": SERVER_PORT,
            "RCON_PORT": self.rcon,
            "ENABLE_RCON": "true",
            "RCON_PASSWORD": RCON_P,
            "GENERATE_STRUCTURES": "false",
            "SPAWN_ANIMALS": "false",
            "SPAWN_MONSTERS": "false",
            "SPAWN_NPCS": "false",
            "VIEW_DISTANCE": " 5",
            "SEED": 0,
            "LEVEL_TYPE": "FLAT",
            "OPS": "TransformerScorn",
            "MODE": "creative",
            "SPAWN_PROTECTION": "FALSE",
        }
        # offline mode disables OPS so dont use it if we are keeping the server
        # for testing. But normally for running CI we want this option.
        if not KEEP_SERVER:
            env["ONLINE_MODE"] = "FALSE"

        if not data_folder.exists():
            data_folder.mkdir()
        else:
            shutil.rmtree(data_folder)
            data_folder.mkdir()

        container = docker_client.containers.run(
            "itzg/minecraft-server",
            detach=True,
            environment=env,
            network_mode="host",
            # restart_policy={"Name": "always"},
            volumes={str(data_folder): {"bind": "/data", "mode": "rw"}},
            name=self.name,
        )

        return container
