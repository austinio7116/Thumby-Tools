#!/bin/bash
# Run a game in the Linux SDL2 emulator
# Usage: ./run_emulator.sh <GameFolder>
# Example: ./run_emulator.sh Thumbalaga

set -e

GAME="${1:?Usage: ./run_emulator.sh <GameFolder>}"
GAME_NAME=$(basename "$GAME")

MP="/home/maustin/mp-thumby"
ENGINE="$MP/TinyCircuits-Tiny-Game-Engine"
MICROPYTHON="$MP/ports/unix/build-standard/micropython"
FS="$ENGINE/filesystem"

if [ ! -f "$MICROPYTHON" ]; then
    echo "MicroPython not built. Building..."
    (cd "$MP/ports/unix" && make -j8 DEBUG=1 USER_C_MODULES=../../TinyCircuits-Tiny-Game-Engine CFLAGS_EXTRA="-DNDEBUG")
fi

# Sync game to engine filesystem
echo "Syncing $GAME_NAME to emulator filesystem..."
rm -rf "$FS/Games/$GAME_NAME"
cp -r "$GAME" "$FS/Games/$GAME_NAME"

# Run
echo "Launching $GAME_NAME..."
cd "$FS"
"$MICROPYTHON" -X heapsize=2617152 main.py "Games/$GAME_NAME/main.py"
