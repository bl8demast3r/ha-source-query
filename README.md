# Source Server Query

> [!NOTE]
> **AI-generated code.** This integration was written largely by [Claude](https://www.anthropic.com/claude), an AI model by Anthropic, working with the maintainer through Claude Code. It has automated tests and was tested against a live TF2 server, but it has not had an independent human code review. Read the code before you rely on it, and report problems in the [issue tracker](https://github.com/bl8demast3r/ha-source-query/issues).

A Home Assistant integration that monitors Source dedicated servers (srcds) and any other game server that answers Valve's [A2S query protocol](https://developer.valvesoftware.com/wiki/Server_queries): TF2, CS2, Garry's Mod, L4D2, Insurgency, GoldSrc games, and non-Valve games such as Rust, ARK and Valheim.

It is read-only. It asks the server for its public status, the same way the in-game server browser does, and needs no RCON password or server-side plugin.

## Entities

Each server becomes a device with these entities:

| Entity | Notes |
|---|---|
| Online | `binary_sensor`, connectivity. Off when the server stops answering; never unavailable. |
| Players | Current player count. With the player list option on, the connected players are in the `player_list` attribute. |
| Max players | |
| Bots | Many games also count bots in Players. |
| Server name | |
| Map | |
| Game | The game description the server reports, e.g. "Team Fortress". |
| Password protected | `binary_sensor` |
| VAC secured | `binary_sensor`, diagnostic |
| Latency | Round-trip time of the query in ms, diagnostic |
| Version | Diagnostic |
| Tags | `sv_tags`, diagnostic, disabled by default |

When the server is offline, Online turns off and the other entities become unavailable until it answers again. A server that is down when Home Assistant starts still gets set up, so automations like "notify me when the server comes back" work.

### Player list and privacy

The Players sensor's history only records the **count**. The `player_list` attribute (name, score, seconds connected) is a live view: it is excluded from the recorder, so player names are never written to Home Assistant's database. A2S doesn't send SteamIDs or IPs, only display names.

Some games hide or fake the list. CS:GO's `host_players_show` cvar, for example, can limit it to a count only. The integration shows whatever the server sends.

## Installation

### HACS

1. In HACS, open the menu → **Custom repositories**, add this repository's URL, and choose type **Integration**.
2. Install **Source Server Query** and restart Home Assistant.

### Manual

Copy `custom_components/source_query` into your Home Assistant `config/custom_components/` directory and restart.

## Setup

**Settings → Devices & services → Add integration → Source Server Query**, then enter:

- **Host**: hostname or IP of the server.
- **Query port**: usually the game port (27015 by default). Some games answer on a separate port; Rust, for example, often uses the game port + 1.

The server has to answer before it can be added. Home Assistant must be able to reach the query port over **UDP**.

### Options

Open the integration's **Configure** dialog:

- **Polling interval**: 10–3600 seconds, default 30.
- **Fetch player list**: on by default. Turning it off skips the A2S_PLAYER query entirely.

## Load on the server

Each poll is one A2S_INFO exchange and, if enabled, one A2S_PLAYER exchange. Each is a challenge round-trip of a few small UDP packets, so about 8 packets per poll. Public servers already get queried far more often by server browsers and server-list sites. srcds rate-limits queries per IP (`sv_max_queries_sec_global` and related cvars in CS:GO/CS2), and the 10-second minimum interval stays well below those limits.

## Development

```bash
uv venv .venv
uv pip install --python .venv/bin/python --group test
.venv/bin/python -m pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Contributors

- [@bl8demast3r](https://github.com/bl8demast3r): maintainer
- [Claude](https://www.anthropic.com/claude) (Claude Opus 5.5, Anthropic): AI pair programmer; wrote the initial integration, tests and documentation

## License

[MIT](LICENSE)
