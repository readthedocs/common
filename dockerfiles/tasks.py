import os
import sys

from invoke import task

DOCKER_COMPOSE = 'common/dockerfiles/docker-compose.yml'
DOCKER_COMPOSE_SEARCH = 'common/dockerfiles/docker-compose-search.yml'
DOCKER_COMPOSE_WEBPACK = 'common/dockerfiles/docker-compose-webpack.yml'
DOCKER_COMPOSE_ASSETS = 'dockerfiles/docker-compose-assets.yml'
DOCKER_COMPOSE_OVERRIDE = 'docker-compose.override.yml'
DOCKER_COMPOSE_COMMAND = f'docker-compose --project-directory=. -f {DOCKER_COMPOSE} -f {DOCKER_COMPOSE_OVERRIDE} -f {DOCKER_COMPOSE_SEARCH} -f {DOCKER_COMPOSE_WEBPACK}'

@task(help={
    'cache': 'Build Docker image using cache (default: False)',
})
def build(c, cache=False):
    """Build docker image for servers."""
    cache_opt = '' if cache else '--no-cache'
    c.run(f'{DOCKER_COMPOSE_COMMAND} build {cache_opt}', pty=True)

@task(help={
    'command': 'Command to pass directly to "docker-compose"',
})
def compose(c, command):
    """Pass the command to docker-compose directly."""
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
    'webpack': 'Start webpack development server (default: False)',
    'ext-theme': 'Enable new theme from ext-theme (default: False)',
    'scale-build': 'Add additional build instances (default: 1)',
    'ngrok': 'ngrok domain to serve the application. Example: "17b5-139-47-118-243.ngrok.io"',
})
def up(c, search=True, init=False, reload=True, webpack=False, ext_theme=False, scale_build=1, ngrok=""):
    """Start all the docker containers for a Read the Docs instance"""
    cmd = []

    cmd.append('INIT=t' if init else 'INIT=')
    cmd.append('DOCKER_NO_RELOAD=t' if not reload else 'DOCKER_NO_RELOAD=')

    cmd.append('docker-compose')
    cmd.append('--project-directory=.')
    cmd.append(f'-f {DOCKER_COMPOSE}')
    cmd.append(f'-f {DOCKER_COMPOSE_OVERRIDE}')

    if search:
        cmd.append(f'-f {DOCKER_COMPOSE_SEARCH}')
    if webpack:
        # This option implies the theme is enabled automatically
        ext_theme = True
        cmd.append(f'-f {DOCKER_COMPOSE_WEBPACK}')
        cmd.insert(0, 'RTD_EXT_THEME_DEV_SERVER_ENABLED=t')
    if ext_theme:
        cmd.insert(0, 'RTD_EXT_THEME_ENABLED=t')
    if ngrok:
        cmd.insert(0, f'RTD_PRODUCTION_DOMAIN={ngrok}')
        cmd.insert(0, f'NGINX_WEB_SERVER_NAME={ngrok}')
        cmd.insert(0, f'NGINX_PROXITO_SERVER_NAME=*.{ngrok}')

    cmd.append('up')

    cmd.append(f'--scale build={scale_build}')

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

    if backupdb:
        c.run(f'{DOCKER_COMPOSE_COMMAND} {subcmd} database pg_dumpall -c -U docs_user > dump_`date +%d-%m-%Y"_"%H_%M_%S`__`git rev-parse HEAD`.sql', pty=True)

    c.run(f'{DOCKER_COMPOSE_COMMAND} {subcmd} web python3 manage.py {command}', pty=True)

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

@task(help={
    'only_required': 'Only pull the required image (used by default for clonning). Use it if you don\'t need all images (default: False)',
})
def pull(c, only_required=False):
    """Pull all docker images required for build servers."""
    images = [
        ('ubuntu-20.04-2022.02.16', 'ubuntu-20.04'),
    ]
    if not only_required:
        images.extend([
            ('6.0', 'stable'),
            ('7.0', 'latest'),
            ('8.0', 'testing'),
            ('ubuntu-22.04-2022.03.15', 'ubuntu-22.04'),
        ])
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
        c.run(f'{DOCKER_COMPOSE_COMMAND} exec -e GITHUB_USER=$GITHUB_USER -e GITHUB_TOKEN=$GITHUB_TOKEN web tox {arguments}', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} run -e GITHUB_USER=$GITHUB_USER -e GITHUB_TOKEN=$GITHUB_TOKEN --rm --no-deps web tox {arguments}', pty=True)

@task
def buildassets(c):
    """Build all assets for the application and push them to backend storage"""
    c.run(f'docker-compose -f {DOCKER_COMPOSE_ASSETS} run --rm assets bash -c "npm ci && node_modules/bower/bin/bower --allow-root update && npm run build"', pty=True)
    c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web python3 manage.py collectstatic --noinput', pty=True)


@task(help={
    'action': 'Action to realize on Transifex ("pull" or "push")',
})
def translations(c, action):

    if action not in ('pull', 'push'):
        print(f'Action passed ("{action}") not supported. Use "pull" or "push".')
        sys.exit(1)

    transifex_token = os.environ.get('TRANSIFEX_TOKEN', None)
    if not transifex_token:
        print('You need to export TRANSIFEX_TOKEN environment variable.')
        sys.exit(1)


    # Download Transifex Client to be used from inside the container
    if not os.path.exists('tx'):
        download_file = 'https://github.com/transifex/cli/releases/download/v1.1.0/tx-linux-amd64.tar.gz'
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web /bin/bash -c "curl --location {download_file} | tar --extract -z --file=- tx"', pty=True)

    if action == 'pull':
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web ./tx --token {transifex_token} pull --force', pty=True)
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web /bin/bash -c "cd readthedocs/ && python3 ../manage.py makemessages --all"', pty=True)
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web /bin/bash -c "cd readthedocs/ && python3 ../manage.py compilemessages"', pty=True)

    elif action == 'push':
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web /bin/bash -c "cd readthedocs/ && python3 ../manage.py makemessages --locale en"', pty=True)
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web ./tx --token {transifex_token} push --source', pty=True)
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web /bin/bash -c "cd readthedocs/ && python3 ../manage.py compilemessages --locale en"', pty=True)
