"""Thin wrapper over the Docker SDK to control scenario containers.

The orchestrator runs with the host Docker socket mounted, so it can stop and
start the sibling containers that make up the test environment.
"""
import os

import docker

# Container names are pinned in docker-compose.yml.
REDIS_CONTAINER = os.getenv("REDIS_CONTAINER", "ff-redis")
APP_CONTAINER = os.getenv("APP_CONTAINER", "ff-app")
POSTGRES_CONTAINER = os.getenv("POSTGRES_CONTAINER", "ff-postgres")

_client = docker.from_env()


def get_container(name: str):
    return _client.containers.get(name)


def stop_container(name: str) -> None:
    get_container(name).stop(timeout=5)


def start_container(name: str) -> None:
    get_container(name).start()


def container_status(name: str) -> str:
    try:
        return get_container(name).status
    except docker.errors.NotFound:
        return "absent"
