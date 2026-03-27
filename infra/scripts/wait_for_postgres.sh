#!/bin/sh
set -e

until pg_isready -h postgres -p 5432 -U access2; do
  echo "Waiting for postgres..."
  sleep 2
done

echo "Postgres is ready."
