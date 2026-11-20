#!/usr/bin/env python3
"""Read-only plugin metrics and provisional deterministic eligibility assessment."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import sys
import tempfile
import time

KINDS = ('skill', 'command', 'agent', 'hook', 'script', 'rule', 'config',
         'reference', 'evaluation', 'adapter', 'unknown')
TEXT = {'.md', '.txt', '.json', '.yaml', '.yml', '.py', '.sh', '.bash', '.zsh',
        '.js', '.ts', '.tsx', '.jsx', '.toml', '.ini', '.cfg', '.rst'}
SKIP = {'.git', 'node_modules', '.venv', '__pycache__'}
MCP = re.compile(r'\bmcp__[\w-]+__[\w-]+\b')
COMMAND = re.compile(r'^\s*(?:\$\s+)?([a-zA-Z][\w.-]*(?:/[\w.-]+)*)\s+[^\n]+$')
API = re.compile(r'https?://([^/\s`"<>]+)(/[^\s`"<>]*)?')
ANNOTATION_ENUMS = {
    'requiredness': {'required', 'optional', 'unknown'},
    'role': {'core', 'auxiliary', 'unknown'},
    'scope': {'principal', 'mixed', 'unknown'},
    'basis': {'direct', 'interpretation'},
    'origin': {'external_application', 'external_cli', 'hosted_service',
               'bundled_code', 'host_tool', 'unknown'},
}
CACHE_SCHEMA_VERSION = 1
# Version 2 stores validated excerpts privately so cache reads can re-verify
# that each quote still occurs verbatim in the current documents. Version 1
# entries contain only hashes and are ignored (never trusted) as stale format.
CACHE_ANNOTATIONS_VERSION = 2
ROLES = {
    'knowledge': re.compile(r'\b(?:definition|concept|principle|means|définition|principe)\b', re.I),
    'behavioral_policy': re.compile(r'\b(?:must|never|always|do not|interdit|toujours|jamais)\b', re.I),
    'reasoning_procedure': re.compile(r'\b(?:step\s+\d|analy[sz]e|compare|evaluate|étape|comparer)\b', re.I),
    'tool_operation': re.compile(r'\b(?:run|execute|invoke|install|exécuter|installer)\b', re.I),
    'routing': re.compile(r'\b(?:delegate|subagent|route|déléguer)\b', re.I),
}


def read_json(path):
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


def scope_for(parts):
    if any(p in {'tests', 'test', 'evals', 'fixtures'} for p in parts):
        return 'validation'
    if any(p in {'docs', 'examples'} for p in parts) or parts[-1].lower().startswith('readme'):
        return 'documentation'
    if '.claude-plugin' in parts or parts[-1] in {'package.json', 'pyproject.toml'}:
        return 'distribution'
    if any(p in {'skills', 'agents', 'commands', 'hooks', 'rules'} for p in parts):
        return 'runtime'
    return 'unknown'


def kind_for(path):
    parts = path.parts
    if path.name == 'SKILL.md':
        return 'skill'
    for folder, kind in [('tests', 'evaluation'), ('evals', 'evaluation'),
                         ('agents', 'agent'), ('commands', 'command'), ('hooks', 'hook'),
                         ('rules', 'rule')]:
        if folder in parts:
            return kind
    if path.name in {'CLAUDE.md', 'AGENTS.md'}:
        return 'rule'
    if path.suffix.lower() in {'.py', '.sh', '.bash', '.zsh', '.js', '.ts', '.tsx', '.jsx'}:
        return 'script'
    if path.suffix.lower() in {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'}:
        return 'config'
    if path.suffix.lower() in {'.md', '.txt', '.rst'}:
        return 'reference'
    return 'unknown'


def load_annotations(path):
    """Optional advisory annotations; failures never imply absence of dependencies."""
    state = {'provided': False, 'error': None, 'plugins': {}}
    if path is None:
        return state
    state['provided'] = True
    try:
        data = read_json(path)
    except (OSError, ValueError, RecursionError) as exc:
        state['error'] = type(exc).__name__
        return state
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('plugins'), dict):
        state['error'] = 'invalid_schema'
        return state
    state['plugins'] = data['plugins']
    return state


def _validate_claim(claim, documents, prefix='', require_hash=False, retain_excerpt=False):
    if not isinstance(claim, dict):
        return None, prefix + 'claim_not_object'
    file, excerpt, target = (claim.get(field) for field in ('file', 'excerpt', 'target'))
    if not all(isinstance(value, str) and value.strip() for value in (file, excerpt, target)):
        return None, prefix + 'claim_missing_text'
    if Path(file).is_absolute():
        return None, prefix + 'citation_outside_root'
    file = posixpath.normpath(file)
    if file == '..' or file.startswith('../') or file not in documents:
        return None, prefix + 'citation_outside_root_or_unread'
    if excerpt not in documents[file]:
        return None, prefix + 'excerpt_not_verbatim'
    excerpt_sha256 = hashlib.sha256(excerpt.encode()).hexdigest()
    if require_hash:
        stored_hash = claim.get('excerpt_sha256')
        if not isinstance(stored_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', stored_hash):
            return None, prefix + 'claim_invalid_hash'
        if stored_hash != excerpt_sha256:
            return None, prefix + 'claim_excerpt_hash_mismatch'
    for field, allowed in ANNOTATION_ENUMS.items():
        if claim.get(field, 'unknown') not in allowed:
            return None, prefix + 'claim_invalid_' + field
    validated = {'file': file, 'excerpt_sha256': excerpt_sha256, 'target': target,
                 'operation': claim.get('operation'),
                 'requiredness': claim.get('requiredness', 'unknown'),
                 'role': claim.get('role', 'unknown'),
                 'scope': claim.get('scope', 'unknown'),
                 'basis': claim.get('basis', 'unknown'),
                 'origin': claim.get('origin', 'unknown')}
    if retain_excerpt:
        validated['excerpt'] = excerpt
    return validated, None


def validate_annotation(payload, documents, retain_excerpts=False):
    if not isinstance(payload, dict):
        return None, 'annotation_not_object'
    claims = payload.get('claims', [])
    unresolved = payload.get('unresolved', [])
    if not isinstance(claims, list) or not isinstance(unresolved, list) or not all(isinstance(x, str) for x in unresolved):
        return None, 'annotation_shape'
    validated = []
    for claim in claims:
        item, error = _validate_claim(claim, documents, retain_excerpt=retain_excerpts)
        if error:
            return None, error
        validated.append(item)
    return {'claims': validated, 'unresolved': list(unresolved)}, None


def public_annotation(validated):
    """Strip private excerpt text before anything is emitted by scan output."""
    return {'claims': [{key: value for key, value in claim.items() if key != 'excerpt'}
                       for claim in validated['claims']],
            'unresolved': list(validated['unresolved'])}


def validate_cached_annotation(payload, documents):
    if not isinstance(payload, dict):
        return None, 'cache_payload_not_object'
    claims = payload.get('claims', [])
    unresolved = payload.get('unresolved', [])
    if not isinstance(claims, list) or not isinstance(unresolved, list) or not all(isinstance(x, str) for x in unresolved):
        return None, 'cache_payload_shape'
    validated = []
    for claim in claims:
        item, error = _validate_claim(claim, documents, prefix='cache_',
                                      require_hash=True)
        if error:
            return None, error
        validated.append(item)
    return {'claims': validated, 'unresolved': list(unresolved)}, None


def cache_path(cache_dir, digest):
    return cache_dir / (digest + '.json')


def _cache_dir_problem(cache_dir):
    """Return a note when cache_dir is not a private directory we own."""
    try:
        info = cache_dir.lstat()
    except FileNotFoundError:
        return 'cache_directory_missing'
    except OSError:
        return 'cache_directory_invalid'
    if stat.S_ISLNK(info.st_mode):
        return 'cache_directory_symlink'
    if not stat.S_ISDIR(info.st_mode):
        return 'cache_directory_not_directory'
    if getattr(os, 'geteuid', lambda: None)() not in (None, info.st_uid):
        return 'cache_directory_not_owned'
    if stat.S_IMODE(info.st_mode) & 0o077:
        return 'cache_directory_insecure_permissions'
    return None


def _ensure_private_cache_dir(cache_dir):
    """Create missing cache directories without following symlinks.

    Existing directories keep their permissions (never chmod a caller-supplied
    or parent directory); a pre-existing directory that is not private is
    refused instead.
    """
    cache_dir = Path(os.path.abspath(os.fspath(cache_dir)))
    missing = []
    probe = cache_dir
    while True:
        try:
            info = probe.lstat()
        except FileNotFoundError:
            missing.append(probe)
            if probe.parent == probe:
                return 'cache_directory_invalid'
            probe = probe.parent
        except OSError:
            return 'cache_directory_invalid'
        else:
            if stat.S_ISLNK(info.st_mode):
                return 'cache_directory_symlink'
            if not stat.S_ISDIR(info.st_mode):
                return 'cache_directory_not_directory'
            break
    for path in reversed(missing):
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            try:
                info = path.lstat()
            except OSError:
                return 'cache_directory_invalid'
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                return 'cache_directory_symlink'
        except OSError:
            return 'cache_directory_invalid'
    return _cache_dir_problem(cache_dir)


def _load_cache_entry(path):
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, 'cache_unreadable'
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None, 'cache_unreadable'
        with os.fdopen(fd, encoding='utf-8') as handle:
            fd = None
            entry = json.load(handle)
    except (ValueError, RecursionError):
        return None, 'cache_corrupt'
    except OSError:
        return None, 'cache_unreadable'
    finally:
        if fd is not None:
            os.close(fd)
    return entry, None


def read_cache(cache_dir, digest, documents):
    cache_dir = Path(os.path.abspath(os.fspath(cache_dir)))
    if not cache_dir.exists():
        return None, None
    problem = _cache_dir_problem(cache_dir)
    if problem:
        return None, problem
    entry, error = _load_cache_entry(cache_path(cache_dir, digest))
    if error is not None:
        return None, error
    if entry is None:
        return None, None
    if not isinstance(entry, dict) or entry.get('schema_version') != CACHE_SCHEMA_VERSION:
        return None, 'cache_corrupt'
    version = entry.get('annotations_version')
    if version != CACHE_ANNOTATIONS_VERSION:
        if isinstance(version, int) and version < CACHE_ANNOTATIONS_VERSION:
            return None, 'cache_annotations_version_old'
        return None, 'cache_annotations_version_unsupported'
    if entry.get('digest') != digest:
        return None, 'cache_stale'
    validated, error = validate_cached_annotation(entry.get('payload'), documents)
    if error:
        return None, 'cache_invalid'
    plugin_key = entry.get('plugin_key')
    if plugin_key is not None and not isinstance(plugin_key, str):
        return None, 'cache_invalid'
    return {'plugin_key': plugin_key, **validated}, None


def write_cache(cache_dir, digest, plugin_key, payload):
    cache_dir = Path(os.path.abspath(os.fspath(cache_dir)))
    entry = {'schema_version': CACHE_SCHEMA_VERSION,
             'annotations_version': CACHE_ANNOTATIONS_VERSION,
             'digest': digest, 'plugin_key': plugin_key, 'payload': payload}
    temp = None
    try:
        problem = _ensure_private_cache_dir(cache_dir)
        if problem:
            return problem
        fd, temp = tempfile.mkstemp(prefix='.' + digest + '.', suffix='.tmp', dir=cache_dir)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(entry, handle, sort_keys=True)
        os.replace(temp, cache_path(cache_dir, digest))
        return None
    except (OSError, TypeError, ValueError):
        return 'cache_write_failed'
    finally:
        if temp is not None:
            try:
                os.unlink(temp)
            except OSError:
                pass


def scan(root, identities=(), max_bytes=2_000_000, annotations=None, cache_dir=None):
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('plugin root must be a directory')
    counts, scopes, roles, entrypoints = Counter(), Counter(), Counter(), Counter()
    signals, excluded, errors, artifacts = [], [], [], []
    signal_index = {}
    coverage = Counter()
    manifest = {}
    declared = []
    documents = {}
    file_hashes = {}
    configs = {}

    def signal(kind, target, file, line=None, key=None, context='declaration'):
        # Do not copy source lines, arguments, environment values or URL queries.
        scope = scope_for(Path(file).parts)
        identity = (kind, target, scope, context)
        evidence = {'file': file, 'line': line, 'key': key}
        if identity in signal_index:
            observation = signal_index[identity]
            observation['occurrences'] += 1
            if len(observation['evidence']) < 3:
                observation['evidence'].append(evidence)
            return
        observation = {'kind': kind, 'target': target, 'scope': scope,
                       'context': context, 'method': 'static_analysis', 'occurrences': 1,
                       'status': 'observed' if context == 'declaration' else 'candidate',
                       'evidence': [evidence]}
        signal_index[identity] = observation
        signals.append(observation)

    def walk_error(exc):
        errors.append({'file': os.path.relpath(exc.filename, root), 'reason': 'directory_unreadable'})

    for parent, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        for name in sorted(dirs):
            path = Path(parent) / name
            if name in SKIP or path.is_symlink():
                dirs.remove(name)
                excluded.append({'file': str(path.relative_to(root)), 'reason': 'symlink_directory' if path.is_symlink() else 'dependency_directory'})
        dirs.sort()
        for name in sorted(files):
            path = Path(parent) / name
            rel = str(path.relative_to(root))
            coverage['files_discovered'] += 1
            try:
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode):
                    excluded.append({'file': rel, 'reason': 'non_regular_or_symlink'})
                    continue
                coverage['bytes_discovered'] += info.st_size
                kind = kind_for(Path(rel))
                counts[kind] += 1
                scope = scope_for(Path(rel).parts)
                scopes[scope] += 1
                if kind == 'skill' and Path(rel).parts[0] == 'skills':
                    entrypoints['conventional_skills'] += 1
                artifacts.append({'file': rel, 'kind': kind, 'scope': scope})
                if path.suffix and path.suffix.lower() not in TEXT:
                    excluded.append({'file': rel, 'reason': 'unsupported_format'})
                    continue
                if info.st_size > max_bytes:
                    excluded.append({'file': rel, 'reason': 'size_limit'})
                    continue
                # O_NOFOLLOW closes the final-component symlink race.
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, 'rb') as handle:
                    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                        excluded.append({'file': rel, 'reason': 'non_regular_or_symlink'})
                        continue
                    raw = handle.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    excluded.append({'file': rel, 'reason': 'size_limit'})
                    continue
                try:
                    text = raw.decode('utf-8')
                except UnicodeError:
                    if not path.suffix:
                        excluded.append({'file': rel, 'reason': 'unsupported_format'})
                        continue
                    raise
                documents[rel] = text
                file_hashes[rel] = hashlib.sha256(raw).hexdigest()
                coverage['files_read'] += 1
                coverage['bytes_read'] += len(raw)
            except (OSError, UnicodeError) as exc:
                errors.append({'file': rel, 'reason': type(exc).__name__})
                continue

            if path.suffix.lower() == '.json':
                try:
                    data = json.loads(text)
                except (ValueError, RecursionError):
                    errors.append({'file': rel, 'reason': 'invalid_json'})
                    continue
                configs[rel] = data
                if rel == '.claude-plugin/plugin.json':
                    if not isinstance(data, dict):
                        errors.append({'file': rel, 'reason': 'manifest_not_object'})
                        continue
                    manifest = data
                    for field in ('skills', 'commands', 'agents', 'hooks', 'types', 'mcpServers', 'lspServers'):
                        value = data.get(field)
                        paths = [value] if isinstance(value, str) else value if isinstance(value, list) else []
                        for item in paths:
                            if isinstance(item, str):
                                declared.append((field, item))
                        if field == 'types' and value:
                            signal('mod_surface', 'types', rel, key=field)
                if isinstance(data, dict):
                    servers = data.get('mcpServers', {})
                    if isinstance(servers, dict):
                        for server, config in sorted(servers.items()):
                            signal('mcp_server', server, rel, key='mcpServers.' + server)
                            if isinstance(config, dict) and isinstance(config.get('command'), str):
                                signal('executable', Path(config['command'].split()[0]).name if config['command'].split() and re.fullmatch(r'[\w./-]+', config['command'].split()[0]) else '[redacted_or_dynamic]', rel, key='mcpServers.' + server + '.command')
                    if isinstance(data.get('lspServers'), dict):
                        for server in sorted(data['lspServers']):
                            signal('lsp_server', server, rel, key='lspServers.' + server)
                    if isinstance(data.get('hooks'), dict):
                        for event in sorted(data['hooks']):
                            signal('hook_event', event, rel, key='hooks.' + event)
                    if path.name == 'package.json':
                        for field in ('dependencies', 'devDependencies', 'optionalDependencies'):
                            deps = data.get(field)
                            if isinstance(deps, dict):
                                for dep in sorted(deps):
                                    signal('package', dep, rel, key=field + '.' + dep)

            if path.suffix.lower() != '.md':
                continue
            lines = text.lstrip('\ufeff').splitlines()
            fence, shell_fence, frontmatter = None, False, bool(lines and lines[0].strip() == '---')
            for number, line in enumerate(lines, 1):
                stripped = line.strip()
                if frontmatter:
                    for match in MCP.finditer(line):
                        signal('mcp_tool', match.group(), rel, number, context='frontmatter_declaration')
                    if number > 1 and stripped == '---':
                        frontmatter = False
                    continue
                if stripped.startswith(('```', '~~~')):
                    marker = stripped[:3]
                    if fence == marker:
                        fence, shell_fence = None, False
                    elif fence is None:
                        fence = marker
                        shell_fence = stripped[3:].strip().lower() in {'sh', 'bash', 'shell', 'zsh', 'console'}
                    continue
                context = 'code_example' if fence else 'prose_mention'
                for match in MCP.finditer(line):
                    signal('mcp_tool', match.group(), rel, number, context=context)
                if fence:
                    match = COMMAND.match(line) if shell_fence else None
                    if match:
                        signal('command_token', match[1], rel, number, context=context)
                    continue
                if stripped and not stripped.startswith('#'):
                    coverage['prose_lines'] += 1
                    matched = [role for role, pattern in ROLES.items() if pattern.search(line)]
                    roles.update(scope + ':' + role for role in (matched or ['unclassified']))
                for match in API.finditer(line):
                    host = match[1].split('@')[-1].split('?')[0].split('#')[0].rstrip('.,;:!?)]}')
                    signal('url_host', host, rel, number, context=context)
            if frontmatter:
                errors.append({'file': rel, 'reason': 'unterminated_frontmatter'})

    for field, item in declared:
        try:
            target = (root / item).resolve()
        except (OSError, ValueError):
            errors.append({'file': '.claude-plugin/plugin.json', 'key': field, 'reason': 'declared_path_invalid'})
            continue
        if not target.is_relative_to(root):
            errors.append({'file': '.claude-plugin/plugin.json', 'key': field, 'reason': 'declared_path_outside_root'})
        elif not target.exists():
            errors.append({'file': '.claude-plugin/plugin.json', 'key': field, 'reason': 'declared_path_missing'})
        else:
            signal('declared_surface', str(target.relative_to(root)), '.claude-plugin/plugin.json', key=field)
    if not manifest:
        errors.append({'file': '.claude-plugin/plugin.json', 'reason': 'manifest_missing_or_empty'})
    coverage['files_excluded'] = sum('reason' in entry for entry in excluded if entry['reason'] not in {'dependency_directory', 'symlink_directory'})
    coverage['errors'] = len(errors)
    unread_text = any(item['reason'] in {'size_limit', 'non_regular_or_symlink'}
                      and Path(item['file']).suffix.lower() in TEXT for item in excluded)
    candidates = sorted({s['target'] for s in signals if s['kind'] in {'command_token', 'executable', 'package'}})
    digest_source = {
        'files': sorted([rel, sha] for rel, sha in file_hashes.items()),
        'unread': sorted([item.get('file', ''), item.get('reason', '')]
                         for item in excluded + errors),
    }
    content_digest = hashlib.sha256(json.dumps(
        digest_source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assessment = assess(manifest, documents, configs, artifacts, errors, excluded,
                        root=root, annotations=annotations,
                        digest=content_digest, cache_dir=cache_dir)
    annotation_state = assessment['facts']['enrichment']['status']
    return {
        'assessment': assessment, 'content_digest': content_digest,
        'root': str(root), 'installations': list(identities),
        'status': 'partial' if errors or unread_text or annotation_state in {'invalid', 'unavailable'} else 'observed',
        'artifact_counts_by_kind': {kind: counts[kind] for kind in KINDS},
        'artifact_counts_by_scope': dict(sorted(scopes.items())),
        'entrypoint_candidates': dict(sorted(entrypoints.items())), 'artifacts': artifacts,
        'standalone_software_targets': [{'target': name, 'autonomy': 'unknown'} for name in candidates],
        'dependency_roles': [{'target': name, 'role': 'unknown', 'requirement': 'unknown'} for name in candidates],
        'instruction_units_by_role': {'method': 'lexical_line_signals', 'semantic_status': 'unknown',
                                      'counts': dict(sorted(roles.items())), 'exclusive': False},
        'product_specific_references': {'status': 'candidate', 'observations': signals},
        'extraction_coverage': dict(sorted(coverage.items())),
        'excluded': excluded, 'errors': errors,
        'limitations': ['No semantic classification or software autonomy established.',
                        'Commands in fences are examples, not proven runtime dependencies.',
                        'Symlink directories and dependency directories are not traversed.',
                        'No general shell/import analysis; non-Markdown code is inventoried only.',
                        'Directory conventions classify artifacts, not effective host activation.'],
    }


def assess(manifest, documents, configs, artifacts, errors, excluded, root=None,
           annotations=None, digest=None, cache_dir=None):
    """Extract decision facts; evaluate separately without a model or name allowlist."""

    entries = set()
    entry_roots = []
    unresolved = []
    for folder, suffix in [('skills', 'SKILL.md'), ('commands', '.md'), ('agents', '.md'), ('rules', '.md')]:
        declared = manifest.get(folder, [])
        declared = [declared] if isinstance(declared, str) else declared
        if not isinstance(declared, list):
            unresolved.append(folder)
            declared = []
        prefixes = [folder] + [posixpath.normpath(p) for p in declared if isinstance(p, str)]
        entry_roots.append((folder, suffix, prefixes))
        for file in documents:
            if any(file == prefix or file.startswith(prefix.rstrip('/') + '/') for prefix in prefixes):
                relative = Path(file)
                if any(p in {'tests', 'examples', 'fixtures', 'evals', 'node_modules', 'references'} for p in relative.parts):
                    continue
                if (folder == 'skills' and relative.name == suffix) or (folder != 'skills' and relative.suffix.lower() == suffix):
                    entries.add(file)
    facts = {'entries': sorted(entries), 'active_mcp_servers': [], 'mod_modules': [],
             'lifecycle_hook_events': [], 'operational_evidence': [], 'unresolved': unresolved}
    for field in ('types', 'lspServers', 'hooks'):
        if manifest.get(field):
            unresolved.append('declared_runtime_surface:' + field)
    mcp = manifest.get('mcpServers', '.mcp.json')
    if not isinstance(mcp, (dict, str, list)):
        unresolved.append('mcpServers:unsupported')
    if isinstance(mcp, dict):
        facts['active_mcp_servers'] = sorted(mcp)
    else:
        paths = [mcp] if isinstance(mcp, str) else mcp if isinstance(mcp, list) else []
        for path in paths:
            if not isinstance(path, str):
                unresolved.append('mcpServers:unsupported')
                continue
            path = posixpath.normpath(path)
            data = configs.get(path)
            if isinstance(data, dict) and isinstance(data.get('mcpServers'), dict):
                facts['active_mcp_servers'].extend(sorted(data['mcpServers']))
            elif path != '.mcp.json' or any(a['file'] == path for a in artifacts + excluded):
                unresolved.append('mcpServers:' + path)
    hooks = configs.get('hooks/hooks.json')
    if hooks is not None:
        if isinstance(hooks, dict) and set(hooks) == {'modules'} and isinstance(hooks['modules'], list):
            for module in hooks['modules']:
                if not isinstance(module, str):
                    unresolved.append('hooks/hooks.json:unsupported_module')
                    continue
                module = posixpath.normpath('hooks/' + module)
                if any(a['file'] == module for a in artifacts) and Path(module).suffix in {'.tsx', '.ts', '.js', '.mjs'}:
                    facts['mod_modules'].append(module)
                else:
                    unresolved.append('hook_module:' + module)
        elif (isinstance(hooks, dict) and set(hooks) == {'hooks'} and
              isinstance(hooks['hooks'], dict) and
              all(isinstance(event, str) and isinstance(value, list)
                  for event, value in hooks['hooks'].items())):
            facts['lifecycle_hook_events'] = sorted(hooks['hooks'])
        else:
            unresolved.append('hooks/hooks.json:unsupported')
    # Locations, not source excerpts: intent and requirements can contain secrets.
    facts['instruction_intent'] = []
    facts['coverage_gaps'] = []
    required = re.compile(
        r'^\s*(?:[-*]\s+)?(?:(?:you\s+)?must|required\s+to)\s+(run|execute|invoke|use)\s+`?([\w./-]+)'
        r'|(?:^|[.!?]\s+)(?:(?:first|then|next|finally),?\s+)?(run|execute|invoke)\s+`([\w./-]+)[^`]*`', re.I)
    dependency = re.compile(r'\b(?:requires?|prerequisites?|must (?:be installed|have)|API key|running instance|standalone|wrapper)\b', re.I)
    optional = re.compile(r'\b(?:optional|optionally|if available|when available)\b', re.I)
    for file in sorted(entries):
        fenced = False
        for number, line in enumerate(documents[file].splitlines(), 1):
            if line.lstrip().startswith(('```', '~~~')):
                fenced = not fenced
                continue
            if fenced:
                continue
            if re.match(r'^\s*(?:description|intent|purpose)\s*:', line, re.I):
                facts['instruction_intent'].append({'file': file, 'line': number,
                    'signal': 'declared_intent', 'semantics': 'unknown'})
            operation = required.search(line)
            if operation and not optional.search(line):
                explicit = bool(operation[1])
                facts['operational_evidence'].append({'file': file, 'line': number,
                    'signal': 'required_target_operation' if explicit else 'imperative_operation',
                    'operation': (operation[1] or operation[3]).lower(),
                    'target': operation[2] or operation[4],
                    'requiredness': 'explicit' if explicit else 'unknown',
                    'dependency_role': 'unknown'})
            elif dependency.search(line) and not optional.search(line):
                facts['operational_evidence'].append({'file': file, 'line': number,
                    'signal': 'dependency_language', 'requiredness': 'unknown'})
    mcp_paths = {'.mcp.json'}
    if isinstance(mcp, str):
        mcp_paths.add(posixpath.normpath(mcp))
    elif isinstance(mcp, list):
        mcp_paths.update(posixpath.normpath(item) for item in mcp if isinstance(item, str))

    def decision_gap(file):
        rel = Path(file)
        parts = rel.parts
        if any(p in {'tests', 'examples', 'fixtures', 'evals', 'node_modules', 'references'} for p in parts):
            return False
        if rel.name in {'plugin.json', 'hooks.json'} or file in mcp_paths:
            return True
        return any(any(file == prefix or file.startswith(prefix.rstrip('/') + '/') for prefix in prefixes)
                   and ((folder == 'skills' and rel.name == suffix) or
                        (folder != 'skills' and rel.suffix.lower() == suffix))
                   for folder, suffix, prefixes in entry_roots)

    for item in excluded:
        if decision_gap(item['file']):
            facts['coverage_gaps'].append(dict(item))
    facts['unresolved'] += [e['file'] for e in errors]
    facts['unresolved'] += [e['file'] for e in excluded if Path(e['file']).name == 'SKILL.md' or (Path(e['file']).suffix.lower() == '.md' and any(e['file'].startswith(folder + '/') for folder in ('commands', 'agents', 'rules')))]
    # Native MCP references remain unresolved; shell examples alone are not dependencies.
    for file in sorted(entries):
        if MCP.search(documents[file]):
            facts['operational_evidence'].append({'file': file, 'line': None,
                'signal': 'tool_or_shell_example', 'requiredness': 'unknown'})
    enrichment = {'status': 'absent', 'source': 'absent', 'plugin_key': None,
                  'digest': digest, 'claims': [], 'unresolved': [], 'notes': []}
    state = annotations or {'provided': False}
    selected = None
    file_error = None
    file_status = 'invalid'
    file_key = None
    cache_payload = None
    cache_enabled = cache_dir is not None and digest is not None
    if state.get('provided'):
        if state.get('error'):
            file_error = state['error']
            file_status = 'unavailable'
        else:
            keys = []
            if isinstance(manifest.get('name'), str) and manifest['name']:
                keys.append(manifest['name'])
            if root is not None:
                keys.extend([root.name, str(root)])
            file_key = next((key for key in keys if key in state.get('plugins', {})), None)
            if file_key is not None:
                validated, error = validate_annotation(state['plugins'][file_key], documents,
                                                      retain_excerpts=cache_enabled)
                if error:
                    file_error = error
                else:
                    if cache_enabled:
                        # Cache keeps verbatim excerpts so reads can re-verify them;
                        # scan output only ever receives hash-bearing claims.
                        cache_payload = {'claims': validated['claims'],
                                         'unresolved': list(validated['unresolved'])}
                    selected = ('file', file_key, public_annotation(validated))
    if selected is None and cache_enabled:
        cached, note = read_cache(cache_dir, digest, documents)
        if note:
            enrichment['notes'].append(note)
        if cached is not None:
            selected = ('cache', cached.pop('plugin_key', None), cached)
    if selected is not None:
        source, plugin_key, validated = selected
        enrichment.update(status='valid', source=source, plugin_key=plugin_key, **validated)
        if file_error:
            enrichment['notes'].append('file_annotation_rejected')
        if source == 'file' and cache_payload is not None:
            error = write_cache(cache_dir, digest, plugin_key, cache_payload)
            if error:
                enrichment['notes'].append(error)
    elif file_error:
        enrichment.update(status=file_status, error=file_error)
        facts['coverage_gaps'].append({'file': 'annotations:' + (file_key or 'input'),
                                       'reason': file_error})
    facts['enrichment'] = enrichment
    return {'facts_version': 2, 'facts': facts, **evaluate(facts)}


def evaluate(facts):
    """Policy v4: external-provider evidence is explicit, scoped and advisory."""
    claims = facts.get('enrichment', {}).get('claims', [])
    roles = {}
    for claim in claims:
        roles.setdefault(claim.get('target'), set()).add(claim.get('role'))
    contradictory = any('core' in pair and 'auxiliary' in pair for pair in roles.values())
    ambiguous = contradictory or any(claim.get('role') == 'core' and
                                     (claim.get('basis') == 'interpretation' or
                                      claim.get('origin', 'unknown') == 'unknown')
                                     for claim in claims)
    external = {'external_application', 'external_cli', 'hosted_service'}
    external_claims = [claim for claim in claims
                       if claim.get('basis') == 'direct' and
                       claim.get('requiredness') == 'required' and
                       claim.get('role') == 'core' and
                       claim.get('origin') in external]
    external_principal = any(claim.get('scope') == 'principal' for claim in external_claims)
    external_mixed = any(claim.get('scope') in {'mixed', 'unknown'} for claim in external_claims)
    enriched = facts.get('enrichment', {}).get('status') == 'valid' and bool(claims)
    if facts['mod_modules']:
        decision, rule = 'ineligible', 'MOD_RUNTIME'
    elif facts['active_mcp_servers']:
        decision, rule = 'ineligible', 'MCP_RUNTIME'
    elif facts['unresolved'] or facts.get('coverage_gaps'):
        decision, rule = 'needs_review', 'INCOMPLETE_EVIDENCE'
    elif not facts['entries']:
        decision, rule = 'ineligible', 'NO_INSTRUCTION_ENTRY'
    elif ambiguous:
        decision, rule = 'needs_review', 'ENRICHED_AMBIGUOUS'
    elif external_principal:
        decision, rule = 'ineligible', 'ENRICHED_EXTERNAL_CAPABILITY_PROVIDER'
    elif external_mixed:
        decision, rule = 'needs_review', 'EXTERNAL_CAPABILITY_MIXED'
    elif facts['operational_evidence'] and not enriched:
        decision, rule = 'needs_review', 'DEPENDENCY_UNRESOLVED'
    else:
        decision, rule = 'eligible', 'INSTRUCTIONS_NO_DETECTED_BLOCKER'
    return {'rules_version': 4, 'decision': decision, 'rule': rule,
            'qualification': 'provisional; not calibrated confidence'}


def installed_roots(home):
    registry = read_json(home / 'plugins/installed_plugins.json')
    if not isinstance(registry, dict) or registry.get('version') != 2 or not isinstance(registry.get('plugins'), dict):
        raise ValueError('expected installed_plugins.json version 2 with plugins mapping')
    enabled = {}
    settings = home / 'settings.json'
    if settings.exists():
        data = read_json(settings)
        if not isinstance(data, dict) or not isinstance(data.get('enabledPlugins', {}), dict):
            raise ValueError('invalid user settings enabledPlugins')
        enabled = data.get('enabledPlugins', {})
    roots = {}
    for key, entries in sorted(registry['plugins'].items()):
        if not isinstance(entries, list):
            raise ValueError('plugin installations must be lists')
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get('installPath'), str):
                raise ValueError('installation missing installPath')
            identity = {field: entry.get(field) for field in ('scope', 'projectPath', 'version')}
            identity.update({'key': key, 'user_enabled': enabled.get(key), 'effective_enabled': 'unknown'})
            roots.setdefault(Path(entry['installPath']).expanduser().resolve(), []).append(identity)
    return roots


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path)
    parser.add_argument('--installed', action='store_true')
    parser.add_argument('--claude-home', type=Path, default=Path.home() / '.claude')
    parser.add_argument('--max-file-bytes', type=int, default=2_000_000)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--cache-dir', type=Path,
                        default=Path.home() / '.cache/claude-skill-recomposer/annotations')
    parser.add_argument('--no-cache', action='store_true')
    args = parser.parse_args(argv)
    if not (args.paths or args.installed) or args.max_file_bytes <= 0:
        parser.error('provide paths or --installed; max-file-bytes must be positive')
    start = time.perf_counter()
    try:
        roots = installed_roots(args.claude_home) if args.installed else {}
        for path in args.paths:
            roots.setdefault(path.expanduser().resolve(), [])
    except (OSError, ValueError, RecursionError) as exc:
        print(f'discovery failed: {type(exc).__name__}: check registry/settings format and paths', file=sys.stderr)
        return 1
    annotations = load_annotations(args.annotations)
    cache_dir = None if args.no_cache else args.cache_dir.expanduser()
    results = []
    for root, identities in sorted(roots.items()):
        try:
            results.append(scan(root, identities, args.max_file_bytes, annotations, cache_dir))
        except (OSError, ValueError, RecursionError):
            results.append({'root': str(root), 'installations': identities, 'status': 'error',
                            'errors': [{'reason': 'root_unreadable_or_invalid'}]})
    json.dump({'schema_version': 1, 'heuristics_version': 1, 'plugins': results}, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')
    print(f'{len(results)} plugins; {time.perf_counter() - start:.3f}s including JSON output; 0 LLM calls', file=sys.stderr)
    return 2 if any(p['status'] != 'observed' for p in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
