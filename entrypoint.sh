#!/bin/bash
set -e

# Wait for database to be ready (if DATABASE_URL is set)
if [ -n "$DATABASE_URL" ] || [ -n "$DB_HOST" ]; then
    echo "Waiting for database..."

    # Simple wait loop - in production, use something like wait-for-it.sh
    sleep 2
fi

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Execute the main command
exec "$@"
