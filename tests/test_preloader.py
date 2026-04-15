from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.preloader import preload_repo_context


def test_preload_repo_context_scans_real_repo(tmp_path: Path):
    (tmp_path / 'README.md').write_text('# Demo\n\nRepo intro\n', encoding='utf-8')
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts' / 'run.py').write_text('print("hi")\n', encoding='utf-8')
    (tmp_path / '.env').write_text('SECRET=1\n', encoding='utf-8')

    request = SkillCreateRequestV6(task='scan repo', repo_paths=[str(tmp_path)])
    context = preload_repo_context(request)

    paths = {item['path'] for item in context['selected_files']}
    assert 'README.md' in paths
    assert 'scripts/run.py' in paths
    assert '.env' not in paths
    assert context['repos'][0]['exists'] is True


def test_preload_repo_context_scans_repo_inside_hidden_parent(tmp_path: Path):
    repo_root = tmp_path / '.workspace' / 'demo-repo'
    repo_root.mkdir(parents=True)
    (repo_root / 'README.md').write_text('# Demo\n\nRepo intro\n', encoding='utf-8')
    (repo_root / 'scripts').mkdir()
    (repo_root / 'scripts' / 'run.py').write_text('print("hi")\n', encoding='utf-8')

    request = SkillCreateRequestV6(task='scan repo', repo_paths=[str(repo_root)])
    context = preload_repo_context(request)

    paths = {item['path'] for item in context['selected_files']}
    assert 'README.md' in paths
    assert 'scripts/run.py' in paths
    assert context['repos'][0]['exists'] is True


def test_preload_repo_context_marks_missing_repo():
    request = SkillCreateRequestV6(task='scan repo', repo_paths=['/tmp/definitely-missing-openclaw-repo'])
    context = preload_repo_context(request)

    assert context['repos'][0]['exists'] is False
    assert context['repos'][0]['selected_files'] == []
    assert context['notes']
