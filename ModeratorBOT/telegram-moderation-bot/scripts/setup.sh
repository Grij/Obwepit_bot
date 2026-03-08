#!/bin/bash
set -e

# Setup script for ModeratorBOT
echo "Installing Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env
fi

echo "Setup complete. Don't forget to edit .env and config/ files."
