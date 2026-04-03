#!/bin/bash
# Remove a game from the Thumby Color device
# Usage: ./device_rm.sh <GameName> [device]
# Example: ./device_rm.sh Thumbalaga

set -e

GAME="${1:?Usage: ./device_rm.sh <GameName> [device]}"
DEV="${2:-/dev/ttyACM0}"

if [ ! -e "$DEV" ]; then
    echo "Device '$DEV' not found."
    exit 1
fi

echo "Removing Games/$GAME from device..."
mpremote connect "$DEV" rm -r ":Games/$GAME" 2>&1 || echo "(may need manual removal for non-empty dirs)"
echo "Done."
