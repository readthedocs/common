import os
import sys
import hashlib

from invoke import task

DOCKER_COMPOSE = 'common/dockerfiles/docker-compose.yml'
DOCKER_COMPOSE_SEARCH = 'common/dockerfiles/docker-compose-search.yml'
DOCKER_COMPOSE_ASSETS = 'dockerfiles/docker-compose-assets.yml'
DOCKER_COMPOSE_OVERRIDE = 'docker-compose.override.yml'
DOCKER_COMPOSE_COMMAND = f'docker compose --project-directory=. -f {DOCKER_COMPOSE} -f {DOCKER_COMPOSE_OVERRIDE} -f {DOCKER_COMPOSE_SEARCH}'

@task(help={
    'cache': 'Build Docker image using cache (default: False)',
})
def build(c, cache=False):
    """Build docker image for servers."""
    cache_opt = '--no-cache' if not cache else ""
    cache_env_var = ""
    if cache and not os.environ.get("PRUNE_PYTHON_PACKAGE_CACHE"):
        files_to_cache = [
            # Community
            "requirements/docker.txt",

            # Corporate
            "../readthedocs.org/requirements/docker.txt",
            "setup.cfg",

            # Both
            "../ext-theme/setup.cfg",
            "../readthedocs-ext/setup.cfg",
        ]

        cache_hash = hashlib.md5()
        for f in files_to_cache:
            if os.path.exists(f):
                cache_hash.update(open(f, mode="rb").read())
        cache_hash = cache_hash.hexdigest()
        cache_env_var = f"PRUNE_PYTHON_PACKAGE_CACHE={cache_hash}"

    c.run(f'{cache_env_var} {DOCKER_COMPOSE_COMMAND} build {cache_opt}', echo=True, pty=True)

@task(help={
    'command': 'Command to pass directly to "docker compose"',
})
def compose(c, command):
    """Pass the command to docker compose directly."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} {command}', pty=True)

@task(help={
    'volumes': 'Delete all the data storaged in volumes as well (default: False)',
})
def down(c, volumes=False):
    """Stop and remove all the docker containers."""
    if volumes:
        c.run(f'{DOCKER_COMPOSE_COMMAND} down -v', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} down', pty=True)

@task(help={
    'search': 'Start search container (default: True)',
    'init': 'Perform initialization steps (default: False)',
    'reload': 'Enable automatic process reloading (default: True)',
    'build': 'Enable automatic building (default: False)',
    'detach': 'Detach mode: run containers in the background (default: False)',
    'scale-build': 'Add additional build instances (default: 1)',
    'http-domain': 'Configure a production domain for HTTP traffic. Subdomains included, '
                   'example.dev implies *.examples.dev for proxito. Example: '
                   '"17b5-139-47-118-243.ngrok.io"',
    'log-level': 'Logging level for the Django application (default: INFO)',
    'django-debug': 'Sets the DEBUG Django setting (default: True)',
})
def up(c, search=True, init=False, reload=True, build=False, detach=False, scale_build=1, http_domain="", django_debug=True, log_level='INFO'):
    """Start all the docker containers for a Read the Docs instance"""
    cmd = []

    cmd.append('INIT=t' if init else 'INIT=')
    cmd.append('DOCKER_NO_RELOAD=t' if not reload else 'DOCKER_NO_RELOAD=')
    cmd.append(f'RTD_LOGGING_LEVEL={log_level}')

    cmd.append('docker compose')
    cmd.append('--project-directory=.')
    cmd.append(f'-f {DOCKER_COMPOSE}')
    cmd.append(f'-f {DOCKER_COMPOSE_OVERRIDE}')

    if search:
        cmd.append(f'-f {DOCKER_COMPOSE_SEARCH}')
    if django_debug:
        cmd.insert(0, 'RTD_DJANGO_DEBUG=t')
    if http_domain:
        cmd.insert(0, f'RTD_PRODUCTION_DOMAIN={http_domain}')
        cmd.insert(0, f'RTD_PUBLIC_DOMAIN={http_domain}')
        cmd.insert(0, f'NGINX_WEB_SERVER_NAME={http_domain}')
        cmd.insert(0, f'NGINX_PROXITO_SERVER_NAME=*.{http_domain}')

    cmd.append('up')

    cmd.append(f'--scale build={scale_build}')

    if detach:
        cmd.append('--detach')
    if build:
        cmd.append('--build')

    c.run(' '.join(cmd), pty=True)


@task(help={
    'running': 'Open the shell in a running container',
    'container': 'Container to open the shell (default: web)'
})
def shell(c, running=True, container='web'):
    """Run a shell inside a container."""
    if running:
        c.run(f'{DOCKER_COMPOSE_COMMAND} exec {container} /bin/bash', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm {container} /bin/bash', pty=True)

@task(help={
    'command': 'Command to pass directly to "django-admin" inside the container',
    'running': 'Execute "django-admin" in a running container',
    'backupdb': 'Backup postgres database before running Django "manage" command',
})
def manage(c, command, running=True, backupdb=False):
    """Run manage.py with a specific command."""
    subcmd = 'run --rm'
    if running:
        subcmd = 'exec'

    # After you run this and upgrade the DB:
    # inv docker.shell --container database --no-running
    # dropdb -U docs_user docs_db
    # createdb -U docs_user docs_db
    # psql -U docs_user docs_db < dump_*.sql
    # If upgrading Postgres versions, you may need to run:
    # ALTER USER docs_user WITH ENCRYPTED PASSWORD 'docs_pwd';
    if backupdb:
        c.run(f'{DOCKER_COMPOSE_COMMAND} {subcmd} database pg_dumpall -c -U docs_user > dump_`date +%d-%m-%Y"_"%H_%M_%S`__`git rev-parse HEAD`.sql', pty=True)

    c.run(f'{DOCKER_COMPOSE_COMMAND} {subcmd} web uv run python3 manage.py {command}', pty=True)

@task(help={
    'container': 'Container to attach',
})
def attach(c, container):
    """Attach a tty to a running container (useful for pdb)."""
    prefix = c['container_prefix'] # readthedocsorg or readthedocs-corporate
    c.run(f'docker attach --sig-proxy=false --detach-keys="ctrl-p,ctrl-p" {prefix}_{container}_1', pty=True)

@task(help={
    'containers': 'Container(s) to restart (it may restart "nginx" container if required)',
})
def restart(c, containers):
    """Restart one or more containers."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} restart {containers}', pty=True)

    # When restarting a container that nginx is connected to, we need to restart
    # nginx as well because it has the IP cached
    need_nginx_restart = [
        'web',
        'proxito',
        'storage',
    ]
    for extra in need_nginx_restart:
        if extra in containers:
            c.run(f'{DOCKER_COMPOSE_COMMAND} restart nginx', pty=True)
            break

@task()
def pull(c):
    """Pull all docker images required for build servers."""
    images = [
        ('ubuntu-22.04-2023.03.09', 'ubuntu-22.04'),
        ('ubuntu-24.04-2024.06.17', 'ubuntu-24.04'),
    ]
    for image, tag in images:
        c.run(f'docker pull readthedocs/build:{image}', pty=True)
        c.run(f'docker tag readthedocs/build:{image} readthedocs/build:{tag}', pty=True)

@task(help={
    'arguments': 'Arguments to pass directly to "tox" command',
    'running': 'Run all tests in a running container',
})
def test(c, arguments='', running=True):
    """Run all test suite using ``tox``."""
    if running:
        c.run(f'{DOCKER_COMPOSE_COMMAND} exec -e GITHUB_USER=$GITHUB_USER -e GITHUB_TOKEN=$GITHUB_TOKEN web uv run tox {arguments}', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} run -e GITHUB_USER=$GITHUB_USER -e GITHUB_TOKEN=$GITHUB_TOKEN --rm --no-deps web uv run tox {arguments}', pty=True)

@task(help={
    'tool': 'build.tool to compile (python, nodejs, rust, golang)',
    'version': 'specific version for the tool',
    'os': 'ubuntu-20.04, ubuntu-22.04, ubuntu-24.04 (default)',
})
def compilebuildtool(c, tool, version, os=None):
    """Compile a ``build.tools`` to be able to use that tool/version from a build in a quick way."""
    from readthedocs.builds.constants_docker import RTD_DOCKER_BUILD_SETTINGS

    valid_oss = list(RTD_DOCKER_BUILD_SETTINGS['os'].keys())
    if not os:
        # Skip `latest` version
        # https://github.com/readthedocs/readthedocs.org/blob/7f9c8fd4f306479f228bb9aac02dd70f35270618/readthedocs/builds/constants_docker.py#L88
        os = valid_oss[-2]

    if os not in valid_oss:
        print(f'Invalid os. You must specify one of {", ".join(valid_oss)}')
        sys.exit(1)

    valid_tools = RTD_DOCKER_BUILD_SETTINGS['tools'].keys()
    if tool not in valid_tools:
        print(f'Invalid tool. You must specify one of {", ".join(valid_tools)}')
        sys.exit(1)

    valid_versions = RTD_DOCKER_BUILD_SETTINGS['tools'][tool].keys()
    if version not in valid_versions:
        print(f'Invalid version for the specified tool. You must specify one of {", ".join(valid_versions)}')
        sys.exit(1)

    final_version = RTD_DOCKER_BUILD_SETTINGS['tools'][tool][version]

    c.run(f'OS={os} ./scripts/compile_version_upload_s3.sh {tool} {final_version}')
