#!/bin/bash
# List files on the Thumby Color device
# Usage: ./device_ls.sh [path] [device]
# Example: ./device_ls.sh
#          ./device_ls.sh Games/Thumbalaga

DEV="${2:-/dev/ttyACM0}"
PATH_ARG="${1:-}"

if [ ! -e "$DEV" ]; then
    echo "Device '$DEV' not found."
    exit 1
fi

if [ -n "$PATH_ARG" ]; then
    mpremote connect "$DEV" ls ":$PATH_ARG/"
else
    mpremote connect "$DEV" ls :
fi
