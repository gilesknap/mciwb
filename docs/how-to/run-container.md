# Run in a container

Pre-built containers with mciwb and its dependencies already
installed are available on [Github Container Registry](https://ghcr.io/gilesknap/mciwb).

The container has the `mciwb` command as its entrypoint. It can connect to a
Minecraft server with `mciwb shell` or `mciwb run`, but it cannot start or
stop servers: `mciwb start`, `stop`, `backup` and `restore` need a host
install of mciwb (see {doc}`../tutorials/installation`) because they control
docker and the server's files.

## Starting the container

To check the version in the container:

```
$ docker run --rm ghcr.io/gilesknap/mciwb:latest --version
```

To open an interactive shell connected to a server started on the same
machine with `mciwb start`, use host networking so that `localhost:20100`
reaches the server, and `-it` for an interactive terminal:

```
$ docker run --rm -it --network host ghcr.io/gilesknap/mciwb:latest shell --player YOUR_NAME
```

To run a build script from the current folder:

```
$ docker run --rm --network host -v $(pwd):/work ghcr.io/gilesknap/mciwb:latest run /work/build.py
```

To get a released version, use a numbered release instead of `latest`.
