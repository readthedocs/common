#!/usr/bin/env bash
# Dev entrypoint for the isolated-builders pattern.
#
# Emulates the production AMI's two systemd units —
# ``readthedocs-builder-setup.service`` (clone + worker venv setup) and
# then ``readthedocs-celery-worker.service`` (start the worker) — as
# one foreground bash script. No systemd, no New Relic, no Sentry:
# dev only.
#
# Compose wiring is in ``common/dockerfiles/docker-compose.yml`` under
# the ``isolated-builder`` service.

set -euo pipefail

# Required variable
: "${RTD_BROKER_URL:?RTD_BROKER_URL must be set (e.g. redis://cache:6379/0)}"

# Optional variables with defaults
: "${RTD_BUILDS_QUEUE:=isolated-builds}"
: "${RTD_BUILDER_REPO:=https://github.com/readthedocs/readthedocs-builder.git}"
: "${RTD_BUILDER_REF:=main}"
: "${RTD_BUILDER_TOKEN:=}"

SRC="/usr/src/builder/checkouts/readthedocs-builder"
VENV="/usr/src/builder/venv"
UV_PYTHON_DIR="/usr/src/builder/uv-python"
DOCROOT="${RTD_DOCROOT:-/home/docs/checkouts}"

# 1. Clone (or skip if the host's checkout is bind-mounted in).
#    A bind-mount means $SRC is already populated; we skip ``git clone``
#    so dev iteration on the runner code (edit on host, restart the
#    container) doesn't blow the host checkout away.
if [ -z "$(ls -A "$SRC" 2>/dev/null)" ]; then
    echo "[isolated-builder] $SRC empty; cloning $RTD_BUILDER_REPO@$RTD_BUILDER_REF ..."
    clone_url="$RTD_BUILDER_REPO"
    if [ -n "$RTD_BUILDER_TOKEN" ] && [ "${RTD_BUILDER_REPO#https://}" != "$RTD_BUILDER_REPO" ]; then
        clone_url="https://${RTD_BUILDER_TOKEN}@${RTD_BUILDER_REPO#https://}"
    fi
    git clone --depth=1 --branch "$RTD_BUILDER_REF" "$clone_url" "$SRC"
else
    echo "[isolated-builder] $SRC already populated; skipping clone (dev bind-mount)."
fi

# 1b. The docroot is a named volume shared with the build containers, and
#     docker creates named volumes root-owned. Every command in the build
#     container runs as ``docs``, so it has to own this or the very first
#     ``mkdir`` fails — silently, because that command is ``record=False``
#     (which implies warn-only), leaving the next command to die on a cwd
#     that was never created.
#
#     ``docs`` is uid 1005 / gid 205 in the readthedocs/build images. Given
#     by number rather than name because that user doesn't exist in THIS
#     container. Production has it as a real user: Packer creates the host
#     ``docs`` with the same ids and the worker runs as it, which is what
#     makes the shared mount need no translation.
mkdir -p "$DOCROOT"
chown "${RTD_DOCKER_UID:-1005}:${RTD_DOCKER_GID:-205}" "$DOCROOT"

# 2. Build the venv against a uv-managed Python 3.14. One venv holds
#    everything: ``--package worker`` pulls in ``builder`` too, since the
#    worker runs it in-process. Same flags as the prod systemd setup unit,
#    minus the ``observability`` extra (no New Relic / Sentry in dev).
#
#    Idempotent: ``uv sync --frozen`` is a no-op when the venv already
#    matches uv.lock from a previous run.
echo "[isolated-builder] Syncing venv at $VENV (managed Python under $UV_PYTHON_DIR) ..."
cd "$SRC"
UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" \
UV_PROJECT_ENVIRONMENT="$VENV" \
    uv sync --frozen --package worker --python 3.14 --python-preference=only-managed

# 3. Replace this process with the Celery worker. PYTHONPATH points at
#    the worker/ project dir so ``-A worker.celery`` resolves from the
#    live source; --max-tasks-per-child=1 so the worker exits after one
#    task (matches prod's ephemeral pattern, even though there's no AWS
#    API call to terminate anything in dev — the worker just exits and
#    compose can be configured to restart or not).
echo "[isolated-builder] Starting Celery worker on queue '$RTD_BUILDS_QUEUE' ..."
export PYTHONPATH="$SRC/worker"

CMD="$VENV/bin/celery -A worker.celery worker --loglevel=INFO --concurrency=1 --max-tasks-per-child=1 -Q ${RTD_BUILDS_QUEUE}"
if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  exec $CMD
else
  echo "Running process with reload"
  exec nodemon --config /usr/src/builder/checkouts/nodemon.json --exec $CMD
fi
