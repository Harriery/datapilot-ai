"""Keep main only; preserve other tips in remote archive tags and a local bundle.

Default: inspect only. --apply: archive first, then delete branches using leases.
Uncommitted tracked work, unfinished operations and additional worktrees block it.
No source merging is performed: unique old work remains available in the archive.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess


class GitError(RuntimeError):
    pass


def git(root: Path, *args: str, check: bool = True):
    result = subprocess.run(['git', *args], cwd=root, text=True, capture_output=True)
    if check and result.returncode:
        raise GitError(result.stderr.strip() or result.stdout.strip() or 'Git command failed')
    return result


def consolidate(root: Path, *, apply: bool = False) -> dict:
    root = Path(git(root, 'rev-parse', '--show-toplevel').stdout.strip())
    for args in [('diff', '--quiet'), ('diff', '--cached', '--quiet')]:
        if git(root, *args, check=False).returncode:
            raise GitError('Tracked changes exist. Commit them before branch cleanup.')
    for marker in ['MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply']:
        path = Path(git(root, 'rev-parse', '--git-path', marker).stdout.strip())
        if (path if path.is_absolute() else root / path).exists():
            raise GitError('Finish the current Git operation before branch cleanup.')
    if git(root, 'worktree', 'list', '--porcelain').stdout.count('worktree ') != 1:
        raise GitError('Additional worktrees exist; their branches must be reviewed first.')
    # No fetch, switch, tags or deletions during the default inspection.
    lines = git(root, 'ls-remote', '--heads', 'origin').stdout.splitlines()
    remote = dict((line.split()[1][len('refs/heads/'):], line.split()[0]) for line in lines)
    if 'main' not in remote:
        raise GitError('origin/main does not exist.')
    local = {}
    for line in git(root, 'for-each-ref', '--format=%(objectname) %(refname)', 'refs/heads').stdout.splitlines():
        sha, ref = line.split(maxsplit=1)
        local[ref[len('refs/heads/'):]] = sha
    remote_other = {name: sha for name, sha in remote.items() if name != 'main'}
    local_other = {name: sha for name, sha in local.items() if name != 'main'}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    backup = root.parent / (root.name + '-branch-backups') / (stamp + '.bundle')
    result = {'remote_branches': len(remote_other), 'local_branches': len(local_other),
              'backup': str(backup), 'applied': False}
    if not apply:
        return result
    git(root, 'fetch', 'origin', '+refs/heads/*:refs/remotes/origin/*')
    # Fetch must still describe the snapshot we will archive and delete.
    for name, sha in remote.items():
        if git(root, 'rev-parse', 'refs/remotes/origin/' + name).stdout.strip() != sha:
            raise GitError('A remote branch changed during inspection; rerun cleanup.')
    if 'main' in local and git(root, 'merge-base', '--is-ancestor', local['main'], remote['main'], check=False).returncode:
        raise GitError('Local main has independent commits. Merge/review them before cleanup.')
    backup.parent.mkdir(parents=True, exist_ok=True)
    git(root, 'bundle', 'create', str(backup), '--all')
    git(root, 'bundle', 'verify', str(backup))
    git(root, 'switch', 'main') if 'main' in local else git(root, 'switch', '-c', 'main', '--track', 'origin/main')
    git(root, 'merge', '--ff-only', 'origin/main')
    if git(root, 'rev-parse', 'HEAD').stdout.strip() != remote['main']:
        raise GitError('Local main changed during cleanup; no branches were deleted.')
    tags = []
    for category, branches in [('remote', remote_other), ('local', local_other)]:
        for name, sha in branches.items():
            tag = f'archive/{stamp}/{category}/{name}'
            git(root, 'tag', tag, sha)
            tags.append('refs/tags/' + tag)
    if tags:
        # Every archive must be remotely reachable before ANY branch is deleted.
        git(root, 'push', '--atomic', 'origin', *[ref + ':' + ref for ref in tags])
    if remote_other:
        leases = [f'--force-with-lease=refs/heads/{name}:{sha}' for name, sha in remote_other.items()]
        deletes = [f':refs/heads/{name}' for name in remote_other]
        git(root, 'push', '--atomic', *leases, 'origin', *deletes)
    for name in local_other:
        # Both the verified bundle and the published tags preserve these commits.
        if git(root, 'rev-parse', 'refs/heads/' + name).stdout.strip() != local_other[name]:
            raise GitError('A local branch changed during cleanup; it was not deleted.')
        git(root, 'branch', '-D', '--', name)
    git(root, 'fetch', '--prune', 'origin')
    remaining = git(root, 'ls-remote', '--heads', 'origin').stdout.splitlines()
    if any(line.split()[1] != 'refs/heads/main' for line in remaining):
        raise GitError('Another branch appeared concurrently; archived cleanup finished but review the new branch.')
    result.update(applied=True, archive_prefix='archive/' + stamp + '/')
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Archive and remove all branches except main.')
    args = parser.parse_args(argv)
    try:
        result = consolidate(Path.cwd(), apply=args.apply)
    except (GitError, OSError) as exc:
        print('STOP:', exc)
        return 1
    print('Remote branches to archive:', result['remote_branches'])
    print('Local branches to archive:', result['local_branches'])
    print('Backup:', result['backup'])
    print('DONE: main is the only branch; old work is in archive tags.' if result['applied']
          else 'Inspection only. Use --apply to archive and clean up.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
