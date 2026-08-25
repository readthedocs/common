#!/usr/bin/env bash
# Dev entrypoint for the build-isolated pattern.
#
# Emulates the production AMI's two systemd units —
# ``readthedocs-builder-setup.service`` (clone + worker venv setup) and
# then ``readthedocs-celery-worker.service`` (start the worker) — as
# one foreground bash script. No systemd, no New Relic, no Sentry:
# dev only.
set -euo pipefail

# Required variable
: "${RTD_BROKER_URL:?RTD_BROKER_URL must be set (e.g. redis://cache:6379/0)}"

# Optional variables with defaults
: "${RTD_BUILDS_QUEUE:=build:isolated}"
: "${RTD_BUILDER_REF:=main}"

SRC="/usr/src/builder/checkouts/readthedocs-builder"
VENV="/usr/src/builder/venv"
UV_PYTHON_DIR="/usr/src/builder/uv-python"
DOCROOT="${RTD_DOCROOT:-/home/docs/checkouts}"

# 1. Check if readthedocs-builder is mounted from the host and fail otherwise.
if [ -z "$(ls -A "$SRC" 2>/dev/null)" ]; then
    echo "$SRC empty; failing ..."
    echo "You need to clone readthedocs-builder into the host path that is bind-mounted to $SRC."
else
    echo "$SRC already populated; skipping clone (dev bind-mount)."
fi

# 1. The docroot is a named volume shared with the build containers, and
#    docker creates named volumes root-owned. Every command in the build
#    container runs as ``docs``, so it has to own this or the very first
#    ``mkdir`` fails — silently.
#
#    ``docs`` is uid 1005 / gid 205 in the readthedocs/build images. Given
#    by number rather than name because that user doesn't exist in THIS
#    container. Production has it as a real user: Packer creates the host
#    ``docs`` with the same ids and the worker runs as it, which is what
#    makes the shared mount need no translation.
mkdir -p "$DOCROOT"
chown "${RTD_DOCKER_UID:-1005}:${RTD_DOCKER_GID:-205}" "$DOCROOT"

# 2. Build the venv against a uv-managed Python 3.14.
#    Idempotent: ``uv sync --frozen`` is a no-op when the venv already
#    matches uv.lock from a previous run.
echo "Syncing venv at $VENV (managed Python under $UV_PYTHON_DIR) ..."
cd "$SRC"
UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" \
UV_PROJECT_ENVIRONMENT="$VENV" \
    uv sync --frozen --package worker --python 3.14 --python-preference=only-managed

# 3. Replace this process with the Celery worker. PYTHONPATH points at
#    the worker/ project dir so ``-A worker.celery`` resolves from the
#    live source.
echo "Starting Celery worker on queue '$RTD_BUILDS_QUEUE' ..."
export PYTHONPATH="$SRC/worker"

CMD="$VENV/bin/celery -A worker.celery worker --loglevel=INFO --concurrency=1 --max-tasks-per-child=1 -Q ${RTD_BUILDS_QUEUE}"
if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  exec $CMD
else
  echo "Running process with reload"
  exec nodemon --config /usr/src/builder/checkouts/nodemon.json --exec $CMD
fi
