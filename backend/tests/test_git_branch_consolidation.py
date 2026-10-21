"""Exercise actual Git repositories, archives and lease failure, without network."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('branch_cleanup', Path(__file__).resolve().parents[2] / 'scripts/consolidate_git_branches.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


def run(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / 'remote.git'; remote.mkdir()
    run(remote, 'init', '--bare')
    root = tmp_path / 'project'; root.mkdir()
    run(root, 'init', '-b', 'main')
    run(root, 'config', 'user.name', 'Test')
    run(root, 'config', 'user.email', 'test@example.invalid')
    (root / 'source.txt').write_text('main')
    run(root, 'add', 'source.txt'); run(root, 'commit', '-m', 'Main')
    run(root, 'remote', 'add', 'origin', str(remote))
    run(root, 'push', '-u', 'origin', 'main')
    run(root, 'switch', '-c', 'unique/old-work')
    (root / 'unique.txt').write_text('keep this work')
    run(root, 'add', 'unique.txt'); run(root, 'commit', '-m', 'Independent old work')
    run(root, 'push', '-u', 'origin', 'unique/old-work')
    return root


def test_inspect_does_not_switch_create_tags_or_delete(repo):
    before = run(repo, 'show-ref')
    result = cleanup.consolidate(repo)
    assert result['remote_branches'] == result['local_branches'] == 1
    assert not result['applied'] and not Path(result['backup']).exists()
    assert run(repo, 'show-ref') == before
    assert run(repo, 'branch', '--show-current') == 'unique/old-work'


def test_unique_commits_and_untracked_files_survive_main_only_cleanup(repo):
    old = run(repo, 'rev-parse', 'HEAD')
    (repo / 'my-report.json').write_text('untouched')
    result = cleanup.consolidate(repo, apply=True)
    assert result['applied']
    assert run(repo, 'branch', '--format=%(refname:short)') == 'main'
    heads = run(repo, 'ls-remote', '--heads', 'origin')
    assert heads.endswith('refs/heads/main') and len(heads.splitlines()) == 1
    tags = run(repo, 'ls-remote', '--tags', 'origin')
    assert old in tags and '/remote/unique/old-work' in tags and '/local/unique/old-work' in tags
    assert (repo / 'my-report.json').read_text() == 'untouched'
    assert run(repo, 'show', result['archive_prefix'] + 'remote/unique/old-work:unique.txt') == 'keep this work'
    assert 'refs/heads/unique/old-work' in run(repo, 'bundle', 'list-heads', result['backup'])


def test_dirty_work_blocks_archival_and_branch_deletion(repo):
    (repo / 'unique.txt').write_text('uncommitted')
    with pytest.raises(cleanup.GitError, match='Tracked changes'):
        cleanup.consolidate(repo, apply=True)
    assert 'unique/old-work' in run(repo, 'ls-remote', '--heads', 'origin')
    assert run(repo, 'tag') == ''


def test_concurrently_updated_branch_is_not_deleted(repo, monkeypatch):
    original_git = cleanup.git
    old = run(repo, 'rev-parse', 'unique/old-work')
    new = run(repo, 'rev-parse', 'main')
    def race(root, *args, **kwargs):
        if args[:2] == ('push', '--atomic') and any(arg.startswith('--force-with-lease=') for arg in args):
            run(repo, '--git-dir=' + str(repo.parent / 'remote.git'), 'update-ref', 'refs/heads/unique/old-work', new, old)
        return original_git(root, *args, **kwargs)
    monkeypatch.setattr(cleanup, 'git', race)
    with pytest.raises(cleanup.GitError):
        cleanup.consolidate(repo, apply=True)
    assert new in run(repo, 'ls-remote', '--heads', 'origin', 'unique/old-work')
    assert old in run(repo, 'ls-remote', '--tags', 'origin')
    assert 'unique/old-work' in run(repo, 'branch', '--format=%(refname:short)')
