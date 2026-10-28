"""Compatibility entry point for the provenance-aware archival adapter replay.

Preserves original capture/request clocks. Does not fabricate a fresh frame or
infer semantic observations/fitment from manual SAM boxes. No network calls.
"""
import asyncio

from replay_observation_adapters import main


if __name__ == '__main__':
    asyncio.run(main())
