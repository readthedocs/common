Read the Docs common development files
======================================

Common shared bits for development and release tooling across multiple
repositories.

Installing
----------

To install::

    git submodule add git@github.com:rtfd/common.git common
    git submodule update
    make -f common/common.mk

Setup
-----

The release process automatically handles updating the changelog and incrementing
a version in setup.cfg. You'll need a few extra piece to make this work in each
repository: a version to manipulate and information on the repo for changelog
automation.

There are several options that can come under the ``tool:release`` section:

github_owner
    The GitHub repository owner name

github_repo
    The GitHub repository name

github_private
    Is the repository private? This also requires the use of a GITHUB_TOKEN
    environment variable when pulling changelog. You can generate this at:
    https://github.com/settings/tokens

Additionally, setup.cfg can track all of the setup.py options in plaintext.
For an example of how to migrate all the setup.py options to setup.cfg, see
readthedocs.org or readthedocs-corporate.

Here's an example configuration::

    [metadata]
    version = 1.0.0

    [tool:release]
    github_owner = rtfd
    github_repo = readthedocs.org
    github_private = False
