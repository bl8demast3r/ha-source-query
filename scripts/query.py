"""Query a server the way the integration does and print what it would see.

Usage: .venv/bin/python scripts/query.py HOST [PORT]
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import a2s

from custom_components.source_query.const import (
    DEFAULT_PORT,
    QUERY_TIMEOUT,
)
from custom_components.source_query.coordinator import (
    QUERY_ERRORS,
    async_query_info,
)


async def main(host: str, port: int) -> int:
    """Print the A2S_INFO and A2S_PLAYER replies."""
    try:
        info = await async_query_info(host, port)
    except QUERY_ERRORS as err:
        print(f"A2S_INFO to {host}:{port} failed: {err!r}")
        print("The integration would report this server as offline.")
        return 1

    print(f"A2S_INFO from {host}:{port}")
    for field, value in vars(info).items():
        print(f"  {field}: {value!r}")
    print(f"  (latency: {info.ping * 1000:.1f} ms)")

    try:
        players = await a2s.aplayers((host, port), timeout=QUERY_TIMEOUT)
    except QUERY_ERRORS as err:
        print(f"A2S_PLAYER failed: {err!r} (server would still show online)")
        return 0

    print(f"A2S_PLAYER: {len(players)} entries")
    for player in players:
        print(f"  {player.name!r} score={player.score} {int(player.duration)}s")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    sys.exit(
        asyncio.run(
            main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else DEFAULT_PORT)
        )
    )
