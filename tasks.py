# -*- coding: utf-8 -*-
"""
Read the Docs common tasks.

This is used from a repository that uses the common repository. You can see what
tasks are available with::

    invoke -l

To get more info on tasks::

    invoke -h setup-labels
"""

import os
from collections import namedtuple

from invoke import task

# Label class used below for setup-labels
Label = namedtuple('Label', ['name', 'color', 'desc', 'transpose'])


@task
def setup_labels(ctx, repo, dry_run=False):
    """Setup shared repository labels

    You can specify ``--dry-run/-d`` in order to avoid making changes
    immediately. Note that the actual actions will differ on a live run as the
    list of labels is polled twice.
    """
    try:
        from github import Github, GithubException
    except ImportError:
        print('Python package PyGithub is missing.')
        return False

    if 'GITHUB_TOKEN' not in os.environ.keys():
        print('\n'.join(textwrap.wrap(
            'GITHUB_TOKEN env variable is required. Set up a personal token here:\n'
            'https://github.com/settings/tokens'
        )))
        return False

    # Current base for labels across repos
    labels = [
        Label('Accepted', '10ff91', 'Accepted issue on our roadmap', []),
        Label('Bug', 'FF666E', 'A bug', ['bug']),
        Label('Design', 'e10c02', 'Design or UX/UI related', []),
        Label('Feature', '5319e7', 'New feature', ['Feature Overview']),
        Label('Good First Issue', 'bfe5bf', 'Good for new contributors', ['good first issue']),

        Label('Improvement', 'e2419d', 'Minor improvement to code', ['enhancement', 'Enhancement']),

        Label('Needed: design decision', '54473F', 'A core team decision is required', []),
        Label('Needed: documentation', '54473F', 'Documentation is required', []),
        Label('Needed: more information', '54473F', 'A reply from issue author is required', []),
        Label('Needed: patch', '54473F', 'A pull request is required', []),
        Label('Needed: replication', '54473F', 'Bug replication is required', []),
        Label('Needed: tests', '54473F', 'Tests are required', []),

        Label('Operations', '0052cc', 'Operations or server issue', []),

        Label('PR: hotfix', 'fbca04', 'Pull request applied as hotfix to release', []),
        Label('PR: work in progress', 'F0EDF9', 'Pull request is not ready for full review', []),

        Label('Priority: high', 'e11d21', 'High priority', ['High Priority', 'Priority: High']),
        Label('Priority: low', '4464d6', 'Low priority', ['Priority: Low']),

        Label('Sprintable', 'fef2c0', 'Small enough to sprint on', []),

        Label('Status: blocked', 'd0d0c0', 'Issue is blocked on another issue', []),
        Label('Status: stale', 'd0d0c0', 'Issue will be considered inactive soon', []),

        Label('Support', '5494E8', 'Support question', ['question', 'Question']),
    ]

    # Labels we determined we don't use
    delete_labels = [
        'duplicate',
        'help wanted',
        'invalid',
        'wontfix',
        'PR: ready for review',
        'Status: duplicate',
        'Status: invalid',
        'Status: rejected',
    ]

    api = Github(os.environ.get('GITHUB_TOKEN'))
    repo = api.get_repo(repo)

    # First pass: create expected labels, try to repurpose old labels if
    # possible first.
    try:
        existing_labels = list(repo.get_labels())
    except GithubException:
        print('Repository not found, check that `repo` argument is correct')
        return False
    for label in labels:
        found = None

        for existing_label in existing_labels:
            if label.name == existing_label.name:
                found = existing_label
                break
        if not found:
            for existing_label in existing_labels:
                if existing_label.name in label.transpose:
                    found = existing_label
                    break

        # Modify or create a new label. We can't detect changes here as
        # description is never available on the label object
        if found:
            print('Updating label: {0}'.format(found.name))
            if not dry_run:
                found.edit(label.name, label.color, label.desc)
        else:
            print('Creating label: {0}'.format(label.name))
            if not dry_run:
                repo.create_label(label.name, label.color, label.desc)

    # Second pass, we:
    #
    # * Labels that should be deleted
    # * Labels that can't be transpose directly, issues need to be moved
    # * Notes unknown labels
    untouched = set()
    for label in repo.get_labels():
        if label.name in delete_labels:
            print('Deleting label: {0}'.format(label.name))
            if not dry_run:
                label.delete()
        elif label.name in [l.name for l in labels]:
            pass
        else:
            transpose = False
            for our_label in labels:
                if label.name in our_label.transpose:
                    for issue in repo.get_issues(labels=[label]):
                        print('Adding label for issue: issue={0} label={1}'.format(
                            issue,
                            our_label.name,
                        ))
                        if not dry_run:
                            issue.add_to_labels(our_label.name)
                    print('Deleting label: {0}'.format(label.name))
                    if not dry_run:
                        label.delete()
                    transpose = True
                    break

            if not transpose:
                untouched.add(label)

    if untouched:
        print('Did not do anything with the following labels:')
        for label in untouched:
            print(' - {0}'.format(label.name))
