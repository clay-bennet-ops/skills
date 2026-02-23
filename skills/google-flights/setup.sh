#!/bin/bash
set -e
echo "Installing flight-search dependencies..."
pip install flights 2>/dev/null || pip3 install flights 2>/dev/null || python3 -m pip install flights
mkdir -p "$(dirname "$0")/data"
echo "Done. flight-search is ready."
