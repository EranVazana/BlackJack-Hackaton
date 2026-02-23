#!/bin/bash
# Run Blackjack Server

cd "$(dirname "$0")/../../.."
echo "🎰 Starting Blackjack Server..."
python -m server.server
