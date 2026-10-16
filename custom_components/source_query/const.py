"""Constants for the Source Server Query integration."""

DOMAIN = "source_query"

DEFAULT_PORT = 27015

# Polling interval bounds, in seconds. The floor keeps us well clear of
# srcds's per-IP query rate limiter.
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

CONF_PLAYER_LIST = "player_list"
DEFAULT_PLAYER_LIST = True

# Seconds to wait for each UDP reply. A query with a challenge round-trip
# waits up to twice this.
QUERY_TIMEOUT = 3.0
