"""
A simple CLI for running a sample server.
"""

import os
import sys
import time
from multiprocessing import Process

import uvicorn


def run_server(**kwargs):
    for k, v in kwargs.items():
        os.environ[k] = v

    uvicorn.run("tileadder.server.app:app", host="0.0.0.0")


def main():
    try:
        run = sys.argv[1] == "run"
        dev = sys.argv[2] == "dev"
        prod = sys.argv[2] == "prod"
    except IndexError:
        print("Only supported command is tileadder run dev or tilemaker run prod")
        exit(1)

    if run and dev:
        environment = {
            "TILEADDER_AUTH_TYPE": "mock",
            "TILEADDER_APP_BASE_URL": "http://localhost:8000",
        }

        background_process = Process(target=run_server, kwargs=environment)
        background_process.start()

        while True:
            time.sleep(1)
    if run and prod:
        background_process = Process(target=run_server)
        background_process.start()

        while True:
            time.sleep(1)
