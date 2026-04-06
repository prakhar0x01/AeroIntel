# Step 1: Single shared state module to avoid shared memory reference bugs
# All modules (Inversion, API, WebSocket) must read/write from this same list instance.

aircraft_store: list = []
alert_store: list = []
