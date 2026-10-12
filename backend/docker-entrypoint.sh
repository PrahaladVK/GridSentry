#!/bin/sh
set -e

# First start on an empty volume: download the dataset, load it and train the models.
if [ ! -f "$GRIDSENTRY_ARTIFACTS_DIR/gridsentry.db" ]; then
    echo "No database found in $GRIDSENTRY_ARTIFACTS_DIR, seeding (takes a few minutes)..."
    python seed.py
fi

exec "$@"
