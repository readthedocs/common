from invoke import task

DOCKER_COMPOSE = 'common/dockerfiles/docker-compose.yml'
DOCKER_COMPOSE_SEARCH = 'common/dockerfiles/docker-compose-search.yml'
DOCKER_COMPOSE_OVERRIDE = 'docker-compose.override.yml'
DOCKER_COMPOSE_COMMAND = f'docker-compose -f {DOCKER_COMPOSE} -f {DOCKER_COMPOSE_OVERRIDE} -f {DOCKER_COMPOSE_SEARCH}'

@task(help={
    'cache': 'Build Docker image using cache (default: False)',
})
def build(c, cache=False):
    """Build docker image for servers."""
    cache_opt = '' if cache else '--no-cache'
    c.run(f'{DOCKER_COMPOSE_COMMAND} build {cache_opt}', pty=True)

@task
def compose(c, command):
    """Pass the command to docker-compose directly."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} {command}', pty=True)

@task
def down(c, volumes=False):
    """Stop and remove all the docker containers."""
    if volumes:
        c.run(f'{DOCKER_COMPOSE_COMMAND} down -v', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} down', pty=True)

@task
def up(c, no_search=False, init=False, no_reload=False, scale_build=1):
    """Start all the docker containers for a Read the Docs instance"""
    INIT = 'INIT='
    DOCKER_NO_RELOAD = 'DOCKER_NO_RELOAD='
    SCALE = f'--scale build={scale_build}'
    if init:
        INIT = 'INIT=t'
    if no_reload:
        DOCKER_NO_RELOAD = 'DOCKER_NO_RELOAD=t'

    if no_search:
        c.run(f'{INIT} {DOCKER_NO_RELOAD} docker-compose -f {DOCKER_COMPOSE} -f {DOCKER_COMPOSE_OVERRIDE} up {SCALE}', pty=True)
    else:
        c.run(f'{INIT} {DOCKER_NO_RELOAD} {DOCKER_COMPOSE_COMMAND} up {SCALE}', pty=True)

@task
def shell(c, running=False, container='web'):
    """Run a shell inside a container."""
    if running:
        c.run(f'{DOCKER_COMPOSE_COMMAND} exec {container} /bin/bash', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm {container} /bin/bash', pty=True)

@task
def manage(c, command):
    """Run manage.py with a specific command."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm web python3 manage.py {command}', pty=True)

@task
def attach(c, container):
    """Attach a tty to a running container (useful for pdb)."""
    prefix = c['container_prefix'] # readthedocsorg or readthedocs-corporate
    c.run(f'docker attach --sig-proxy=false {prefix}_{container}_1', pty=True)

@task
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
    'only_latest': 'Only pull the latest tag. Use if you don\'t need all images (default: False)',
})
def pull(c, only_latest=False):
    """Pull all docker images required for build servers."""
    images = [
        ('6.0', 'latest')
    ]
    if not only_latest:
        images.extend([
            ('5.0', 'stable'),
            ('7.0', 'testing'),
        ])
    for image, tag in images:
        c.run(f'docker pull readthedocs/build:{image}', pty=True)
        c.run(f'docker tag readthedocs/build:{image} readthedocs/build:{tag}', pty=True)

@task
def test(c, arguments=''):
    """Run all test suite."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm --no-deps web tox {arguments}', pty=True)
