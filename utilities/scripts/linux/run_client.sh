#!/bin/bash
# Run Blackjack CLI Client

cd "$(dirname "$0")/../../.."
echo "🃏 Starting Blackjack CLI Client..."
python -m client.cli
