#!/bin/bash
# Deploy a game folder to Thumby Color via mpremote
# Usage: ./deploy.sh <GameName> [device]
# Example: ./deploy.sh Thumbalaga
#          ./deploy.sh Thumbalaga /dev/ttyACM1
#
# Looks for the game in TinyCircuits-Thumby-Color-Games/<GameName>/

set -e

GAMES_DIR="/home/maustin/thumby-color/TinyCircuits-Thumby-Color-Games"
GAME_NAME="${1:?Usage: ./deploy.sh <GameName> [device]}"
DEV="${2:-/dev/ttyACM0}"
GAME="$GAMES_DIR/$GAME_NAME"

if [ ! -d "$GAME" ]; then
    echo "Error: Game folder '$GAME' not found"
    exit 1
fi

if [ ! -e "$DEV" ]; then
    echo "Error: Device '$DEV' not found. Is the Thumby Color connected?"
    echo "  WSL2: Run in PowerShell (Admin):"
    echo "    usbipd list"
    echo "    usbipd bind --busid <BUSID>"
    echo "    usbipd attach --wsl --busid <BUSID>"
    exit 1
fi

echo "=== Deploying $GAME_NAME to $DEV ==="

# Create directories
echo "Creating directories..."
mpremote connect "$DEV" mkdir ":Games/$GAME_NAME" 2>/dev/null || true

find "$GAME" -type d | while read -r dir; do
    rel="${dir#$GAME}"
    if [ -n "$rel" ]; then
        echo "  mkdir :Games/$GAME_NAME$rel"
        mpremote connect "$DEV" mkdir ":Games/$GAME_NAME$rel" 2>/dev/null || true
    fi
done

# Upload all files (skip generator scripts and __pycache__)
echo "Uploading files..."
find "$GAME" -type f \
    ! -name "generate_*.py" \
    ! -name "process_*.py" \
    ! -name "*.pyc" \
    ! -path "*__pycache__*" \
    | while read -r file; do
    rel="${file#$GAME/}"
    echo "  $rel"
    mpremote connect "$DEV" cp "$file" ":Games/$GAME_NAME/$rel"
done

echo ""
echo "=== Upload complete! ==="
echo "Resetting device..."
mpremote connect "$DEV" reset
echo "Done! Select $GAME_NAME from the launcher."
