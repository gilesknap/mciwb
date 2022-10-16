#!/bin/bash

# This script runs the tests inside the build container
# useful for verifying that the CI will work as this is how it runs the tests

podman run --rm -v /tmp:/tmp -v \
    /run/user/1000/podman/podman.sock:/var/run/docker.sock \
    --privileged --init --net host  build bash