#!/bin/sh
set -e

cp -n .env.example .env || true
docker compose up --build
