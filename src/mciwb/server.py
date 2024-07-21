"""
Functions for launching and controlling a Minecraft server in a Docker container.
"""

import shutil
from datetime import datetime
from pathlib import Path
from time import sleep

from docker import from_env
from docker.models.containers import Container
from mcipc.rcon.je.client import Client
from mcwb import Vec3

from mciwb.logging import log

HOST = "localhost"

# the default locally mapped backup folder for minecraft data
backup_folder_default = Path.home() / "mciwb-backups"
server_name = "mciwb-server"
default_server_folder = Path.home() / server_name

def_pass = "default_pass"
def_port = 20100
def_world_type = "normal"


class MinecraftServer:
    """
    Create an monitor Minecraft servers on the local machine using Docker

    :param name: the name of the server
    :param rcon: the rcon port for the server
    :param password: the rcon password for the server
    :param server_folder: the folder to store the server files in
    :param world_type: the type of world to create
    :param keep: keep the server running after tests
    :param test: run the server in test mode
    """

    def __init__(
        self,
        name: str,
        rcon: int,
        password: str,
        server_folder: Path,
        world_type: str,
        backup_folder: Path = None,  # type: ignore
        keep: bool = True,
        test=False,
    ) -> None:
        """
        Create a `MinecraftServer` object only. Use `create` to
        spin up the container.
        """
        self.rcon = rcon
        self.port = rcon + 1
        self.name = name
        self.password = password
        self.server_folder = server_folder
        self.backup_folder = backup_folder or backup_folder_default
        self.world = self.server_folder / "world"
        self.world_type = world_type
        self.container: Container | None = None
        self.keep = keep
        self.test = test

    def wait_server(self: "MinecraftServer"):
        """
        Wait until the server is ready to accept rcon connections
        """

        start_time: datetime = datetime.now()
        timeout = 200

        assert isinstance(self.container, Container)

        self.container.reload()
        if self.container.status != "running":
            logs = "\n".join(str(self.container.logs()).split(r"\n"))
            raise RuntimeError(f"minecraft server failed to start\n\n{logs}")

        log.info("waiting for server to come online ...")
        for block in self.container.logs(stream=True):
            log.debug(block.decode("utf-8").strip())
            if b"RCON running" in block:
                break
            elapsed = datetime.now() - start_time
            if elapsed.total_seconds() > timeout:
                raise RuntimeError("Timeout Starting minecraft")

        # wait until a connection is available
        for _ in range(10):
            try:
                with Client(HOST, self.rcon, passwd=self.password):
                    pass
                break
            except ConnectionRefusedError:
                sleep(2)
        else:
            raise RuntimeError("Timeout Starting minecraft")
        log.info(f"Server {self.name} is online on port {self.port}")

    def stop(self):
        """
        Stop the minecraft server
        """
        assert isinstance(self.container, Container)
        log.info(f"Stopping Minecraft Server {self.name} ...")
        self.container.stop()
        self.container.wait()

        log.info(f"Stopped Minecraft Server {self.name} ...")

    def start(self):
        """
        Start the minecraft server
        """
        assert isinstance(self.container, Container)
        log.info(f"Starting Minecraft Server {self.name} on port {self.port}...")
        self.container.start()
        self.wait_server()
        log.info(f"Started Minecraft Server {self.name} ...")

    def remove(self, force=False):
        """
        Remove a minecraft server container

        :param force: force the removal of the container
        """
        # set env var MCIWB_KEEP_SERVER to keep server alive for faster
        # repeated tests and viewing the world with a minecraft client
        if self.container and (not self.keep or force):
            log.info(f"Removing Minecraft Server {self.name} ...")
            self.stop()
            self.container.remove()  # noqa

    def create(self, world_zip=None, force=False) -> None:
        """
        Spin up a minecraft server in a container

        :param world_zip: the zip file to use as the world data. If None is
            provided, a new world will be created.
        :param force: force the server to be removed if it already exists
        """

        # create and launch minecraft container once per session
        docker_client = from_env()

        for container in docker_client.containers.list(all=True):
            assert isinstance(container, Container)
            if container.name == self.name:
                self.container = container
                if force:
                    self.remove(force=True)
                    break
                if container.status == "running":
                    log.info(
                        f"Minecraft Server '{self.name}' "
                        f"already running on port {self.port}"
                    )
                    return
                else:
                    self.start()
                    return

        log.info(f"Launching Minecraft Server '{self.name}' on port {self.port} ...")

        env = {
            "EULA": "TRUE",
            "SERVER_PORT": self.port,
            "RCON_PORT": self.rcon,
            "ENABLE_RCON": "true",
            "RCON_PASSWORD": self.password,
            "SEED": 0,
            "LEVEL_TYPE": self.world_type,
            "MODE": "creative",
            "SPAWN_PROTECTION": 0,
        }

        if self.test:
            env.update(
                {
                    "GENERATE_STRUCTURES": "false",
                    "SPAWN_ANIMALS": "false",
                    "SPAWN_MONSTERS": "false",
                    "SPAWN_NPCS": "false",
                    "VIEW_DISTANCE": " 5",
                    "LEVEL_TYPE": "FLAT",
                    "FORCE_WORLD_COPY": "TRUE",
                }
            )

            # offline mode disables OPS so dont use it if we are keeping the server
            # for local testing. But normally for running CI we want this option.
            if not self.keep:
                env["ONLINE_MODE"] = "FALSE"

        if world_zip:
            env["WORLD"] = str(world_zip)

        if not self.server_folder.exists():
            self.server_folder.mkdir(parents=True)
        elif self.test:
            shutil.rmtree(self.server_folder)
            self.server_folder.mkdir(parents=True)

        if not self.backup_folder.exists():
            self.backup_folder.mkdir(parents=True)

        container = docker_client.containers.run(  # type: ignore
            "docker.io/itzg/minecraft-server",
            detach=True,
            environment=env,
            ports={f"{self.rcon}/tcp": self.rcon, f"{self.port}": self.port},
            restart_policy={"Name": "unless-stopped" if self.keep else "no"},
            volumes={  # type: ignore
                str(self.server_folder): {"bind": "/data", "mode": "rw"},
                str(self.backup_folder): {
                    "bind": str(self.backup_folder),
                    "mode": "rw",
                },
            },
            name=self.name,
            security_opt=["label=disable"],
        )

        assert isinstance(container, Container)
        self.container = container

        self.wait_server()

        self._settings()

    def _settings(self):
        """
        Some default settings for the server that this class creates
        """
        with Client(HOST, self.rcon, passwd=self.password) as client:
            # make sure the local chunk around world centre is loaded
            # this is because the getblock trick needs 0,0,0 in the world
            client.forceload.add((0, 0), (0, 0))

            if not self.test:
                # a nice starting point for the tutorials in seed 0 world
                client.setworldspawn(Vec3(632, 73, -1658))

    @classmethod
    def stop_named(cls, name: str):
        """
        Stop a minecraft server by name

        :param name: the name of the server to stop
        """
        docker_client = from_env()
        for container in docker_client.containers.list(all=True):
            assert isinstance(container, Container)
            if container.name == name:
                log.info(f"Stopping Minecraft Server {name} ...")
                container.stop()
                container.wait()
                container.remove()
                return
        log.warning(f"Minecraft Server '{name}' not found")
