#!/bin/bash
set -e
echo "Installing hotel-search dependencies..."
pip3 install curl-cffi --break-system-packages 2>/dev/null || python3 -m pip install curl-cffi --break-system-packages
mkdir -p "$(dirname "$0")/data"
echo "Done. hotel-search is ready."
