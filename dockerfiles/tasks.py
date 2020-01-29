from invoke import task

DOCKER_COMPOSE = 'common/dockerfiles/docker-compose.yml'
DOCKER_COMPOSE_SEARCH = 'common/dockerfiles/docker-compose-search.yml'
DOCKER_COMPOSE_OVERRIDE = 'docker-compose.override.yml'
DOCKER_COMPOSE_COMMAND = f'docker-compose -f {DOCKER_COMPOSE} -f {DOCKER_COMPOSE_OVERRIDE} -f {DOCKER_COMPOSE_SEARCH}'

@task
def build(c):
    """Build docker image for servers."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} build --no-cache', pty=True)

@task
def down(c, volumes=False):
    """Stop and remove all the docker containers."""
    if volumes:
        c.run(f'{DOCKER_COMPOSE_COMMAND} down -v', pty=True)
    else:
        c.run(f'{DOCKER_COMPOSE_COMMAND} down', pty=True)

@task
def up(c, no_search=False, init=False, no_reload=False):
    """Create an start all the docker containers for a Read the Docs instance."""
    _run_init_command(
        c,
        no_search=no_search,
        init=init,
        no_reload=no_reload,
        command='up',
    )


@task
def start(c, no_search=False, init=False, no_reload=False, containers=''):
    """Start all services (or just selected ones) for a Read the Docs instance in the background."""
    _run_init_command(
        c,
        no_search=no_search,
        init=init,
        no_reload=no_reload,
        command=f'start {containers}',
    )


def _run_init_command(c, *, no_search, init, no_reload, command):
    """Helper for up/start commands."""
    INIT = 'INIT=t' if init else 'INIT='
    DOCKER_NO_RELOAD = 'DOCKER_NO_RELOAD=t' if no_reload else 'DOCKER_NO_RELOAD='

    if no_search:
        c.run(f'{INIT} {DOCKER_NO_RELOAD} docker-compose -f {DOCKER_COMPOSE} -f {DOCKER_COMPOSE_OVERRIDE} {command}', pty=True)
    else:
        c.run(f'{INIT} {DOCKER_NO_RELOAD} {DOCKER_COMPOSE_COMMAND} {command}', pty=True)

@task
def stop(c, containers=''):
    """Stop all services (or just selected ones) of a Read the Docs instance."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} stop {containers}', pty=True)


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

@task
def pull(c):
    """Pull all docker images required for build servers."""
    images = [
        ('4.0', 'stable'),
        ('5.0', 'latest'),
    ]
    for image, tag in images:
        c.run(f'docker pull readthedocs/build:{image}', pty=True)
        c.run(f'docker tag readthedocs/build:{image} readthedocs/build:{tag}', pty=True)

@task
def test(c, arguments=''):
    """Run all test suite."""
    c.run(f'{DOCKER_COMPOSE_COMMAND} run --rm --no-deps web tox {arguments}', pty=True)
