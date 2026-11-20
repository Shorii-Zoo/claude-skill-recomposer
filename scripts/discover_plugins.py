#!/usr/bin/env python3
"""Discover thematic recomposition candidates; never run recomposition."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

# Only implementation modules, never modules from inspected plugin directories.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_plugin_metrics import installed_roots, scan, load_annotations
from cluster_topics import cluster_items

STATE = Path.home() / '.claude/skill-tools/skill-recomposer-state'
CACHE = Path.home() / '.cache/claude-skill-recomposer/annotations'


def load_object(path, default=None):
    if path.is_symlink():
        raise ValueError(f'{path}: symlinked configuration refused')
    if not path.exists():
        return default
    if not path.is_file() or path.stat().st_size > 8_000_000:
        raise ValueError(f'{path}: configuration is not a bounded regular file')
    with path.open(encoding='utf-8') as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected JSON object')
    return value


def blacklist(state, action=None, key=None):
    path = state / 'discover-blacklist.json'
    data = load_object(path, {'schema_version': 1, 'plugins': []})
    if data.get('schema_version') != 1 or not isinstance(data.get('plugins'), list) or not all(isinstance(k, str) and k.strip() for k in data['plugins']):
        raise ValueError('invalid discover blacklist')
    keys = set(data['plugins'])
    if action in {'add', 'remove'}:
        if not key or not key.strip() or any(c in key for c in '\n\r\0'):
            raise ValueError('blacklist requires a non-empty plugin name or registry key')
        if action == 'add':
            keys.add(key)
        else:
            keys.discard(key)
        state.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.discover-blacklist-', dir=state)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump({'schema_version': 1, 'plugins': sorted(keys)}, handle, indent=2)
                handle.write('\n')
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return sorted(keys)


def topics_from(registry):
    result = []
    def visit(items):
        if not isinstance(items, list):
            raise ValueError('registry topic items must be a list')
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('invalid registry topic')
            if item.get('type') != 'topic':
                continue
            if not all(isinstance(item.get(k), str) for k in ('id', 'name', 'short_description', 'scope')):
                raise ValueError('topic missing semantic metadata')
            result.append({'id': 'topic:' + item['id'], 'kind': 'topic', 'name': item['name'],
                           'description': item['short_description'], 'text': item['scope'],
                           'segments': [item['name'], item['short_description'], item['scope']]
                           + [s.strip() for s in re.split(r'[.!?;]\s+|\n', item['scope']) if s.strip()]})
            visit(item.get('items', []))
    visit(registry.get('topics', []))
    return result


def managed_artifacts(registry, state):
    paths, hashes = set(), set()
    artifacts = registry.get('artifacts', [])
    if not isinstance(artifacts, list):
        raise ValueError('registry artifacts must be a list')
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError('invalid registry artifact')
        path = artifact.get('path')
        if isinstance(path, str):
            paths.add((state / path).resolve())
        digest = artifact.get('sha256')
        if isinstance(digest, str):
            hashes.add(digest.lower())
    return paths, hashes


def read_text(path, limit=200_000):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        return None
    try:
        return path.read_bytes().decode('utf-8')
    except (OSError, UnicodeError):
        return None


def metadata(root):
    manifest_path = root / '.claude-plugin/plugin.json'
    if not manifest_path.resolve().is_relative_to(root.resolve()):
        raise ValueError('manifest outside plugin root')
    manifest = load_object(manifest_path, {})
    name = manifest.get('name')
    description = manifest.get('description')
    return (name if isinstance(name, str) and name else root.name,
            description if isinstance(description, str) and description else '')


def instruction_metadata(root, report):
    descriptions = []
    for file in report['assessment']['facts']['entries']:
        path = root / file
        if not path.resolve().is_relative_to(root):
            continue
        text = read_text(path)
        if text is None:
            continue
        lines = text.lstrip('﻿').splitlines()
        description = ''
        if lines and lines[0].strip() == '---':
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    break
                if line.startswith('description:'):
                    description = line.split(':', 1)[1].strip().strip('\"\'')
                    if description in {'>', '|', '>-', '|-'}:
                        block = []
                        for continuation in lines[i + 1:]:
                            if continuation and not continuation.startswith((' ', '\t')):
                                break
                            block.append(continuation.strip())
                        description = ' '.join(block)
                    break
        if not description:
            description = ' '.join(l.strip('# ') for l in lines if l.startswith('# '))
        label = Path(file).parent.name if Path(file).name == 'SKILL.md' else Path(file).stem
        descriptions.append(label + ' ' + description)
        # Preserve concise author-supplied identities as separate topical signals.
        if lines and lines[0].strip() == '---':
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if line.startswith('name:'):
                    descriptions.append(line.split(':', 1)[1].strip())
    return descriptions


def discover(home, state, cache_dir=CACHE, annotations=None, threshold=None):
    registry = load_object(state / 'registry.json', {'topics': [], 'artifacts': []})
    blocked = set(blacklist(state))
    paths, hashes = managed_artifacts(registry, state)
    items = topics_from(registry)
    exclusions, notes = [], []
    for root, identities in sorted(installed_roots(home).items()):
        keys = [identity['key'] for identity in identities]
        try:
            name, description = metadata(root)
        except (OSError, ValueError):
            name, description = root.name, ''
        if name == root.name and keys:
            name = keys[0].split('@')[0]
        identity_names = {name, str(root), *keys, *(k.split('@')[0] for k in keys)}
        reason = None
        if 'skill-recomposer' in identity_names:
            reason = 'self'
        elif (root / 'skills/skill-recomposer/SKILL.md').is_file():
            reason = 'self'
        elif identity_names & blocked:
            reason = 'custom_blacklist'
        elif any(root == path or root.is_relative_to(path) or path.is_relative_to(root) for path in paths):
            reason = 'managed_output'
        elif (root / '.recomposition.json').exists():
            reason = 'managed_output'
        if reason:
            exclusions.append({'name': name, 'keys': keys, 'reason': reason})
            continue
        try:
            report = scan(root, identities, annotations=annotations, cache_dir=cache_dir)
        except (OSError, ValueError, RecursionError):
            # Keep inaccessible installations visible as uncertain, never silently drop them.
            notes.append({'name': name, 'reason': 'scan_failed'})
            exclusions.append({'name': name, 'keys': keys, 'reason': 'scan_failed'})
            continue
        entries = report['assessment']['facts']['entries']
        managed = False
        for file in entries:
            entry = root / file
            if (entry.parent / '.recomposition.json').exists():
                managed = True
                break
            if not entry.resolve().is_relative_to(root):
                managed = True
                break
            text = read_text(entry)
            if text is not None and hashlib.sha256(text.encode('utf-8')).hexdigest() in hashes:
                managed = True
                break
        if managed:
            exclusions.append({'name': name, 'keys': keys, 'reason': 'managed_output'})
            continue
        decision = report['assessment']['decision']
        if decision == 'ineligible':
            exclusions.append({'name': name, 'keys': keys, 'reason': 'ineligible'})
            continue
        segments = instruction_metadata(root, report)
        text = ' '.join(segments)
        if not description:
            description = text[:180] or 'Description indisponible — installation à examiner.'
        items.append({'id': 'plugin:' + str(root), 'kind': 'plugin', 'name': name,
                      'description': description, 'text': text, 'segments': segments, 'decision': decision,
                      'root': str(root), 'keys': keys})
    groups = cluster_items(items, **({'threshold': threshold} if threshold is not None else {}))
    kept = []
    for group in groups:
        members = group['items']
        plugins = [p for p in members if p['kind'] == 'plugin']
        anchors = [p for p in members if p['kind'] == 'topic']
        if plugins and len(members) > 1:
            kept.append({'label': group['label'], 'plugins': plugins, 'topics': anchors})
        else:
            exclusions.extend({'name': p['name'], 'keys': p['keys'], 'reason': 'singleton'} for p in plugins)
    return {'schema_version': 1, 'groups': kept, 'excluded': exclusions, 'notes': notes}


def cell(value):
    value = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))
    return re.sub(r'([\\`*{}\[\]()#+.!<>|_])', r'\\\1', value)


def render(result):
    lines = ['Regroupements indicatifs : ils ne préjugent pas des topics créés par la recomposition.', '']
    for group in result['groups']:
        label = group['label']
        if group['topics']:
            label += ' — topic existant : ' + ', '.join(t['name'] for t in group['topics'])
        lines += ['### ' + cell(label), '', '| Plugin | Courte description | Décision |', '|---|---|---|']
        names = [p['name'] for p in group['plugins']]
        for plugin in group['plugins']:
            name = plugin['name'][:160]
            if names.count(plugin['name']) > 1:
                name += ' (' + ', '.join(plugin['keys']) + '; ' + plugin['root'] + ')'
            description = plugin['description']
            if len(description) > 240:
                description = description[:237].rsplit(' ', 1)[0] + '…'
            lines.append('| ' + ' | '.join((cell(name), cell(description),
                         'Éligible' if plugin['decision'] == 'eligible' else 'À examiner')) + ' |')
        lines.append('')
    if not result['groups']:
        lines.append('Aucun groupe de plugins à proposer après filtrage.')
    else:
        lines.append('Valides-tu les Éligibles uniquement, la liste complète (À examiner inclus), ou une sélection personnalisée ?')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claude-home', type=Path, default=Path.home() / '.claude')
    parser.add_argument('--state-root', type=Path, default=STATE)
    parser.add_argument('--cache-dir', type=Path, default=CACHE)
    parser.add_argument('--no-cache', action='store_true')
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--threshold', type=float)
    parser.add_argument('action', nargs='?', choices=('blacklist',))
    parser.add_argument('blacklist_action', nargs='?', choices=('list', 'add', 'remove'))
    parser.add_argument('key', nargs='?')
    args = parser.parse_args(argv)
    start = time.perf_counter()
    try:
        if args.action:
            if not args.blacklist_action:
                parser.error('blacklist needs list, add, or remove')
            print(json.dumps(blacklist(args.state_root, args.blacklist_action, args.key), ensure_ascii=False))
            return 0
        result = discover(args.claude_home, args.state_root,
                          None if args.no_cache else args.cache_dir,
                          load_annotations(args.annotations) if args.annotations else None,
                          args.threshold)
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else render(result), end='\n' if args.json else '')
        for note in result['notes']:
            print('discover warning: ' + cell(note['name']) + ': ' + note['reason'], file=sys.stderr)
        print(f"discover: {len(result['groups'])} groups; {time.perf_counter() - start:.3f}s", file=sys.stderr)
        return 2 if result['notes'] else 0
    except (OSError, ValueError, RecursionError) as exc:
        print(f'discover failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
