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
: "${RTD_BUILDER_REF:=celery-on-ec2}"
: "${RTD_BUILDER_TOKEN:=}"

SRC="/usr/src/builder/checkouts/readthedocs-builder"
RUNNER_VENV="/usr/src/builder/runner-venv"
UV_PYTHON_DIR="/usr/src/builder/uv-python"
WORKER_VENV="/usr/src/builder/worker-venv"
RCLONE_DIR="/usr/src/builder/rclone"

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

# 1b. Copy the image's rclone onto the host-visible bind-mount.
#     The runner syncs artifacts to storage with rclone from inside the
#     build container, and the worker bind-mounts the binary in rather
#     than each build downloading its own. In production Packer bakes
#     rclone into the AMI, so the worker mounts a real host path.
#
#     Here the worker runs in THIS container, but ``docker run -v`` is
#     resolved by the HOST daemon (docker-out-of-docker via the mounted
#     socket) — so /usr/local/bin/rclone from this image is invisible to
#     it. Copying into $RCLONE_DIR (a host bind-mount, see compose) puts
#     the binary on the host filesystem, same trick as $RUNNER_VENV.
if [ ! -x "$RCLONE_DIR/rclone" ]; then
    echo "[isolated-builder] Copying rclone to $RCLONE_DIR (host-visible for build containers) ..."
    install -m 0755 /usr/local/bin/rclone "$RCLONE_DIR/rclone"
else
    echo "[isolated-builder] $RCLONE_DIR/rclone already present; skipping."
fi

# 2. Pre-build the runner venv against a uv-managed Python 3.14 by
#    syncing the builder/ project. Same flags as the prod systemd setup
#    unit. Both $RUNNER_VENV and $UV_PYTHON_DIR are bind-mounted from
#    host paths (see compose), so the venv's bin/python symlink into
#    $UV_PYTHON_DIR lives on the host filesystem — that's what lets the
#    worker bind-mount the same host paths into build containers it
#    spawns and have the symlink still resolve (matches production).
#
#    Idempotent: ``uv sync --frozen`` is a no-op when the venv
#    already matches uv.lock from a previous run.
echo "[isolated-builder] Syncing runner venv at $RUNNER_VENV (managed Python under $UV_PYTHON_DIR) ..."
cd "$SRC/builder"
UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" \
UV_PROJECT_ENVIRONMENT="$RUNNER_VENV" \
    uv sync --frozen --python 3.14 --python-preference=only-managed

# 3. Worker venv — sync the worker/ project. Dev omits the
#    ``observability`` extra (no New Relic / Sentry in dev).
echo "[isolated-builder] Syncing worker venv at $WORKER_VENV ..."
cd "$SRC/worker"
UV_PROJECT_ENVIRONMENT="$WORKER_VENV" \
    uv sync --frozen --python 3.14

# 4. Replace this process with the Celery worker. PYTHONPATH points at
#    the worker/ project dir so ``-A worker.celery`` resolves from the
#    live source; --max-tasks-per-child=1 so the worker exits after one
#    task (matches prod's ephemeral pattern, even though there's no AWS
#    API call to terminate anything in dev — the worker just exits and
#    compose can be configured to restart or not).
echo "[isolated-builder] Starting Celery worker on queue '$RTD_BUILDS_QUEUE' ..."
export PYTHONPATH="$SRC/worker"

CMD="$WORKER_VENV/bin/celery -A worker.celery worker --loglevel=INFO --concurrency=1 --max-tasks-per-child=1 -Q ${RTD_BUILDS_QUEUE}"
if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  exec $CMD
else
  echo "Running process with reload"
  exec nodemon --config /usr/src/builder/checkouts/nodemon.json --exec $CMD
fi
