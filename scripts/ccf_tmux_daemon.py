#!/usr/bin/env python3
"""Compatibility entrypoint for the local CCF agent dispatcher."""

import sys

from ccf_agent_bridge import main

if __name__ == "__main__":
    raise SystemExit(main(["daemon", *sys.argv[1:]]))
