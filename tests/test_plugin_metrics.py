"""Regression tests for read-only plugin metric extraction."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import extract_plugin_metrics as metrics


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.cache_tmp.cleanup)
        self.cache = Path(self.cache_tmp.name) / 'annotations'
        self.write('.claude-plugin/plugin.json', '{"name":"fixture"}')

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_plugin_aggregation_and_unknown_semantics(self):
        self.write('skills/a/SKILL.md', '---\nname: a\n---\nNever omit evidence.\n')
        self.write('skills/b/SKILL.md', '# Concept\nA definition means something.\n')
        result = metrics.scan(self.root)
        self.assertEqual(result['artifact_counts_by_kind']['skill'], 2)
        self.assertEqual(result['instruction_units_by_role']['semantic_status'], 'unknown')
        self.assertEqual(result['assessment']['decision'], 'eligible')
        self.assertEqual(result['assessment']['rule'], 'INSTRUCTIONS_NO_DETECTED_BLOCKER')
        self.assertEqual(result, metrics.scan(self.root))

    def test_examples_are_not_dependencies_and_secrets_not_copied(self):
        self.write('skills/a/SKILL.md', 'Obsidian is mentioned.\n```sh\nobsidian create --token secret123\n```\nhttps://user:password@example.com/api?token=secret123\n')
        result = metrics.scan(self.root)
        command = next(s for s in result['product_specific_references']['observations'] if s['kind'] == 'command_token')
        self.assertEqual(command['context'], 'code_example')
        self.assertEqual(command['status'], 'candidate')
        self.assertEqual(result['dependency_roles'][0]['requirement'], 'unknown')
        self.assertNotIn('secret123', json.dumps(result))
        self.assertNotIn('password', json.dumps(result))

    def test_non_shell_fences_are_not_commands(self):
        self.write('skills/a/SKILL.md', '```text\nfilename.md description\n```\n```python\nimport os\n```\n')
        observations = metrics.scan(self.root)['product_specific_references']['observations']
        self.assertFalse(any(s['kind'] == 'command_token' for s in observations))

    def test_structural_mcp_and_hook_not_mod(self):
        self.write('.mcp.json', '{"mcpServers":{"service":{"command":"server","env":{"TOKEN":"secret"}}}}')
        self.write('hooks/hooks.json', '{"hooks":{"Stop":[]}}')
        signals = metrics.scan(self.root)['product_specific_references']['observations']
        self.assertEqual(sum(s['kind'] == 'mcp_server' for s in signals), 1)
        self.assertFalse(any(s['kind'] == 'mod_surface' for s in signals))
        self.assertNotIn('secret', json.dumps(signals))

    def test_exclusions_and_invalid_inputs(self):
        self.write('bad.json', '{')
        self.write('big.md', 'x' * 100)
        (self.root / 'binary.md').write_bytes(b'\xff')
        (self.root / 'link.md').symlink_to('/etc/passwd')
        self.write('.claude-plugin/plugin.json', '{"name":"x","skills":"../outside"}')
        result = metrics.scan(self.root, max_bytes=80)
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(any(e['reason'] == 'declared_path_outside_root' for e in result['errors']))
        self.assertTrue(any(e['reason'] == 'size_limit' for e in result['excluded']))
        self.assertTrue(any(e['reason'] == 'non_regular_or_symlink' for e in result['excluded']))

    def test_installed_dedup_preserves_scopes(self):
        self.write('plugins/installed_plugins.json', json.dumps({'version': 2, 'plugins': {'a@m': [
            {'scope': 'user', 'installPath': str(self.root)},
            {'scope': 'project', 'installPath': str(self.root), 'projectPath': '/project'}]}}))
        roots = metrics.installed_roots(self.root)
        self.assertEqual(len(roots), 1)
        self.assertEqual(len(roots[self.root]), 2)
        self.assertEqual(roots[self.root][0]['effective_enabled'], 'unknown')

    def test_mentions_helpers_and_required_engine_contrast(self):
        entry = 'skills/a/SKILL.md'
        for text in ('Compare engine results; explain principles.\n',
                     'Optional: run engine for comparison.\n',
                     '```sh\nengine analyze\n```\n',
                     'Use scripts/check.py as a helper.\n'):
            with self.subTest(text=text):
                self.write(entry, text)
                self.assertEqual(metrics.scan(self.root)['assessment']['decision'], 'eligible')
        self.write(entry, 'description: Compare evidence\nYou must run engine analyze.\n')
        assessment = metrics.scan(self.root)['assessment']
        self.assertEqual(assessment['decision'], 'needs_review')
        evidence = assessment['facts']['operational_evidence'][0]
        self.assertEqual(evidence['target'], 'engine')
        self.assertEqual(evidence['requiredness'], 'explicit')
        self.assertEqual(evidence['dependency_role'], 'unknown')
        self.assertEqual(assessment['facts']['instruction_intent'][0]['line'], 1)

    def test_plain_imperative_operation_is_review(self):
        self.write('skills/a/SKILL.md', 'First, run `engine auth`.\n')
        assessment = metrics.scan(self.root)['assessment']
        self.assertEqual(assessment['decision'], 'needs_review')
        evidence = assessment['facts']['operational_evidence'][0]
        self.assertEqual(evidence['target'], 'engine')
        self.assertEqual(evidence['requiredness'], 'unknown')

    def test_unsupported_hook_shapes_are_unresolved(self):
        self.write('skills/a/SKILL.md', 'Compare claims.')
        for config in ('{"modules":"./x.tsx"}', '{"modules":[1]}',
                       '{"hooks":{"Stop":"not-a-list"}}', '{"hooks":[]}', '[]'):
            with self.subTest(config=config):
                self.write('hooks/hooks.json', config)
                result = metrics.scan(self.root)
                self.assertEqual(result['assessment']['decision'], 'needs_review')
                self.assertEqual(result['assessment']['rule'], 'INCOMPLETE_EVIDENCE')
                self.assertTrue(any('hooks/hooks.json' in item
                                    for item in result['assessment']['facts']['unresolved']))

    def test_event_hook_map_is_lifecycle_not_mod_or_blocker(self):
        self.write('skills/a/SKILL.md', 'Compare claims.\n')
        self.write('hooks/hooks.json', json.dumps({'hooks': {'PostToolUse': [{
            'matcher': 'Edit', 'hooks': [{'type': 'command', 'command': 'secret-bin',
                                          'args': ['--token', 'secret'],
                                          'env': {'TOKEN': 'secret'}}]}]}}))
        result = metrics.scan(self.root)
        self.assertEqual(result['assessment']['decision'], 'eligible')
        self.assertEqual(result['assessment']['facts']['lifecycle_hook_events'], ['PostToolUse'])
        self.assertEqual(result['assessment']['facts']['mod_modules'], [])
        self.assertNotIn('secret', json.dumps(result))

    def test_excluded_instruction_text_marks_partial(self):
        self.write('skills/a/SKILL.md', 'x' * 300)
        result = metrics.scan(self.root, max_bytes=100)
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['errors'])
        self.assertTrue(any(gap['file'].endswith('SKILL.md')
                            for gap in result['assessment']['facts']['coverage_gaps']))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = metrics.main([str(self.root), '--max-file-bytes', '100', '--no-cache'])
        self.assertEqual(code, 2)

    def annotate(self, claims, name='fixture', unresolved=()):
        path = self.write('annotations.json', json.dumps({'schema_version': 1, 'plugins': {
            name: {'claims': claims, 'unresolved': list(unresolved)}}}))
        return metrics.load_annotations(path)

    def claim(self, **overrides):
        claim = {'file': 'skills/a/SKILL.md', 'excerpt': 'Engine is mentioned.',
                 'target': 'engine', 'operation': 'invoke',
                 'requiredness': 'required', 'role': 'core', 'scope': 'principal',
                 'basis': 'direct', 'origin': 'external_application'}
        claim.update(overrides)
        return claim

    def test_annotation_provider_and_optional_claims(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        annotations = self.annotate([self.claim()])
        result = metrics.scan(self.root, annotations=annotations)
        self.assertEqual(result['assessment']['decision'], 'ineligible')
        self.assertEqual(result['assessment']['rule'], 'ENRICHED_EXTERNAL_CAPABILITY_PROVIDER')
        self.assertEqual(result['assessment']['facts']['enrichment']['claims'][0]['target'], 'engine')
        annotations = self.annotate([self.claim(requiredness='optional')])
        self.assertEqual(metrics.scan(self.root, annotations=annotations)['assessment']['decision'],
                         'eligible')
        self.annotate([self.claim()])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = metrics.main([str(self.root), '--annotations', str(self.root / 'annotations.json'),
                                 '--no-cache'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['plugins'][0]['assessment']['rule'],
                         'ENRICHED_EXTERNAL_CAPABILITY_PROVIDER')

    def test_annotation_mixed_scope_and_contradiction(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        annotations = self.annotate([self.claim(scope='mixed')])
        result = metrics.scan(self.root, annotations=annotations)['assessment']
        self.assertEqual(result['rule'], 'EXTERNAL_CAPABILITY_MIXED')
        annotations = self.annotate([self.claim(),
                                     self.claim(role='auxiliary', requiredness='optional')])
        result = metrics.scan(self.root, annotations=annotations)['assessment']
        self.assertEqual(result['rule'], 'ENRICHED_AMBIGUOUS')

    def test_origin_changes_enrichment_outcome(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        result = metrics.scan(self.root, annotations=self.annotate([self.claim(origin='bundled_code')]))
        self.assertEqual(result['assessment']['decision'], 'eligible')
        result = metrics.scan(self.root, annotations=self.annotate([self.claim(origin='unknown')]))
        self.assertEqual(result['assessment']['rule'], 'ENRICHED_AMBIGUOUS')
        result = metrics.scan(self.root, annotations=self.annotate([
            self.claim(role='auxiliary', origin='external_cli')]))
        self.assertEqual(result['assessment']['decision'], 'eligible')

    def test_multiline_description_and_unrelated_excluded_text_do_not_block(self):
        self.write('skills/a/SKILL.md', '---\ndescription: >\n  Compare claims.\n---\nCompare claims.\n')
        self.assertEqual(metrics.scan(self.root)['assessment']['rule'],
                         'INSTRUCTIONS_NO_DETECTED_BLOCKER')
        self.write('notes/random.md', 'x' * 300)
        result = metrics.scan(self.root, max_bytes=100)['assessment']
        self.assertEqual(result['decision'], 'eligible')
        self.assertEqual(result['facts']['coverage_gaps'], [])

    def test_annotation_unresolved_notes_are_informational(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        claim = self.claim(role='auxiliary', requiredness='optional')
        result = metrics.scan(self.root, annotations=self.annotate([claim], unresolved=['check']))
        self.assertEqual(result['assessment']['decision'], 'eligible')
        self.assertEqual(result['assessment']['facts']['enrichment']['unresolved'], ['check'])

    def test_valid_auxiliary_annotation_supersedes_lexical_signal(self):
        self.write('skills/a/SKILL.md', 'Requires scripts/helper.py to count words.\n')
        self.assertEqual(metrics.scan(self.root)['assessment']['rule'], 'DEPENDENCY_UNRESOLVED')
        claim = self.claim(excerpt='Requires scripts/helper.py to count words.',
                           target='helper', requiredness='optional', role='auxiliary')
        result = metrics.scan(self.root, annotations=self.annotate([claim]))['assessment']
        self.assertEqual(result['decision'], 'eligible')
        self.assertEqual(result['rule'], 'INSTRUCTIONS_NO_DETECTED_BLOCKER')
        absent = self.annotate([claim], name='another-plugin')
        self.assertEqual(metrics.scan(self.root, annotations=absent)['assessment']['rule'],
                         'DEPENDENCY_UNRESOLVED')

    def test_annotations_cite_script_and_extensionless_executable(self):
        self.write('skills/a/SKILL.md', 'Compare claims.\n')
        self.write('scripts/helper.sh', 'echo helper\n')
        claim = self.claim(file='scripts/helper.sh', excerpt='echo helper',
                           target='helper', requiredness='required', role='core')
        result = metrics.scan(self.root, annotations=self.annotate([claim]))['assessment']
        self.assertEqual(result['facts']['enrichment']['status'], 'valid')
        self.assertEqual(result['rule'], 'ENRICHED_EXTERNAL_CAPABILITY_PROVIDER')
        self.write('bin/engine', '#!/bin/sh\nengine run\n')
        claim = self.claim(file='bin/engine', excerpt='engine run',
                           target='engine', requiredness='required', role='core')
        result = metrics.scan(self.root, annotations=self.annotate([claim]))['assessment']
        self.assertEqual(result['facts']['enrichment']['status'], 'valid')
        self.assertEqual(result['rule'], 'ENRICHED_EXTERNAL_CAPABILITY_PROVIDER')

    def test_undecodable_extensionless_file_is_unsupported_exclusion(self):
        self.write('skills/a/SKILL.md', 'Compare claims.\n')
        (self.root / 'bin').mkdir(exist_ok=True)
        (self.root / 'bin/blob').write_bytes(b'\xff\xfe')
        result = metrics.scan(self.root)
        self.assertTrue(any(item['file'] == 'bin/blob' and item['reason'] == 'unsupported_format'
                            for item in result['excluded']))
        self.assertFalse(any(item['file'] == 'bin/blob' for item in result['errors']))

    def test_cache_roundtrip_source_and_permissions(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        claim = self.claim(role='auxiliary', requiredness='optional')
        first = metrics.scan(self.root, annotations=self.annotate([claim]), cache_dir=self.cache)
        digest = first['content_digest']
        self.assertEqual(len(digest), 64)
        self.assertEqual(first['assessment']['facts']['enrichment']['source'], 'file')
        entry = self.cache / (digest + '.json')
        self.assertTrue(entry.exists())
        self.assertEqual(entry.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o700)
        second = metrics.scan(self.root, cache_dir=self.cache)
        enrichment = second['assessment']['facts']['enrichment']
        self.assertEqual(second['content_digest'], digest)
        self.assertEqual(enrichment['source'], 'cache')
        self.assertEqual(enrichment['claims'][0]['target'], 'engine')
        self.assertEqual(second['assessment']['decision'], 'eligible')

    def test_cache_ignores_stale_entry_after_edit(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        claim = self.claim(role='auxiliary', requiredness='optional')
        first = metrics.scan(self.root, annotations=self.annotate([claim]), cache_dir=self.cache)
        old_digest = first['content_digest']
        self.write('skills/a/SKILL.md', 'Engine is mentioned. Changed.\n')
        second = metrics.scan(self.root, cache_dir=self.cache)
        self.assertNotEqual(second['content_digest'], old_digest)
        self.assertEqual(second['assessment']['facts']['enrichment']['source'], 'absent')
        self.assertTrue((self.cache / (old_digest + '.json')).exists())

    def test_invalid_annotation_is_not_cached(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        result = metrics.scan(self.root, annotations=self.annotate([self.claim(excerpt='not present')]),
                              cache_dir=self.cache)
        self.assertEqual(result['assessment']['facts']['enrichment']['status'], 'invalid')
        self.assertFalse(self.cache.exists() and any(self.cache.iterdir()))

    def test_no_cache_bypasses_read_and_write(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        self.annotate([self.claim(role='auxiliary', requiredness='optional')])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = metrics.main([str(self.root), '--annotations', str(self.root / 'annotations.json'),
                                 '--cache-dir', str(self.cache), '--no-cache'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['plugins'][0]['assessment']['facts']['enrichment']['source'],
                         'file')
        self.assertFalse(self.cache.exists())
        metrics.scan(self.root, annotations=self.annotate([self.claim(role='auxiliary',
                                                                    requiredness='optional')]),
                     cache_dir=self.cache)
        self.assertEqual(metrics.scan(self.root)['assessment']['facts']['enrichment']['source'], 'absent')

    def test_corrupt_and_stale_cache_entries_are_non_fatal(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        digest = metrics.scan(self.root)['content_digest']
        self.cache.mkdir(parents=True, mode=0o700)
        (self.cache / (digest + '.json')).write_text('{')
        corrupt = metrics.scan(self.root, cache_dir=self.cache)['assessment']['facts']['enrichment']
        self.assertEqual(corrupt['source'], 'absent')
        self.assertIn('cache_corrupt', corrupt['notes'])
        (self.cache / (digest + '.json')).write_text(json.dumps({
            'schema_version': 1, 'annotations_version': 2, 'digest': '0' * 64,
            'plugin_key': 'fixture', 'payload': {'claims': [], 'unresolved': []}}))
        stale = metrics.scan(self.root, cache_dir=self.cache)['assessment']['facts']['enrichment']
        self.assertEqual(stale['source'], 'absent')
        self.assertIn('cache_stale', stale['notes'])

    def write_cache_entry(self, digest, claims, version=2, schema=1):
        self.cache.mkdir(parents=True, mode=0o700, exist_ok=True)
        path = self.cache / (digest + '.json')
        path.write_text(json.dumps({'schema_version': schema,
                                    'annotations_version': version,
                                    'digest': digest, 'plugin_key': 'fixture',
                                    'payload': {'claims': claims, 'unresolved': []}}))
        return path

    def cached_claim(self, **overrides):
        claim = {'file': 'skills/a/SKILL.md', 'excerpt': 'Engine is mentioned.',
                 'excerpt_sha256': hashlib.sha256(b'Engine is mentioned.').hexdigest(),
                 'target': 'engine', 'operation': 'invoke',
                 'requiredness': 'required', 'role': 'core', 'scope': 'principal',
                 'basis': 'direct', 'origin': 'external_application'}
        claim.update(overrides)
        return claim

    def test_cache_persists_private_excerpt_without_public_leak(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        first = metrics.scan(self.root,
                             annotations=self.annotate([self.claim(role='auxiliary',
                                                                  requiredness='optional')]),
                             cache_dir=self.cache)
        entry = json.loads((self.cache / (first['content_digest'] + '.json')).read_text())
        self.assertEqual(entry['annotations_version'], metrics.CACHE_ANNOTATIONS_VERSION)
        self.assertEqual(entry['payload']['claims'][0]['excerpt'], 'Engine is mentioned.')
        self.assertNotIn('excerpt', first['assessment']['facts']['enrichment']['claims'][0])
        self.assertNotIn('Engine is mentioned.', json.dumps(first))
        second = metrics.scan(self.root, cache_dir=self.cache)
        enrichment = second['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'cache')
        self.assertNotIn('excerpt', enrichment['claims'][0])
        self.assertNotIn('Engine is mentioned.', json.dumps(second))

    def test_tampered_cache_forged_excerpt_is_rejected(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        digest = metrics.scan(self.root)['content_digest']
        forged = 'Engine must never be invoked.'
        # New format cannot be forged into trust: role/core changes are ignored
        # when the persisted quote does not occur verbatim in the document.
        claim = self.cached_claim(excerpt=forged,
                                  excerpt_sha256=hashlib.sha256(forged.encode()).hexdigest())
        self.write_cache_entry(digest, [claim])
        result = metrics.scan(self.root, cache_dir=self.cache)
        enrichment = result['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'absent')
        self.assertIn('cache_invalid', enrichment['notes'])
        self.assertEqual(result['assessment']['decision'], 'eligible')
        self.assertEqual(result['assessment']['rule'], 'INSTRUCTIONS_NO_DETECTED_BLOCKER')
        self.assertNotIn(forged, json.dumps(result))

    def test_tampered_cache_missing_excerpt_is_rejected(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        digest = metrics.scan(self.root)['content_digest']
        claim = self.cached_claim()
        del claim['excerpt']
        self.write_cache_entry(digest, [claim])
        result = metrics.scan(self.root, cache_dir=self.cache)
        enrichment = result['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'absent')
        self.assertIn('cache_invalid', enrichment['notes'])
        self.assertEqual(result['assessment']['rule'], 'INSTRUCTIONS_NO_DETECTED_BLOCKER')

    def test_old_annotation_cache_version_is_ignored_not_trusted(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        digest = metrics.scan(self.root)['content_digest']
        claim = self.cached_claim()
        del claim['excerpt']
        self.write_cache_entry(digest, [claim], version=1)
        result = metrics.scan(self.root, cache_dir=self.cache)
        enrichment = result['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'absent')
        self.assertIn('cache_annotations_version_old', enrichment['notes'])
        self.assertEqual(result['assessment']['decision'], 'eligible')
        self.assertEqual(result['assessment']['rule'], 'INSTRUCTIONS_NO_DETECTED_BLOCKER')

    def test_cache_semantics_remain_owner_authored(self):
        # Excerpts are re-verified, but the cache has no secret binding: a local
        # owner can still author arbitrary semantic claims about a real quote.
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        digest = metrics.scan(self.root)['content_digest']
        self.write_cache_entry(digest, [self.cached_claim()])
        enrichment = metrics.scan(self.root,
                                  cache_dir=self.cache)['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'cache')
        self.assertEqual(enrichment['claims'][0]['role'], 'core')

    def test_cache_directory_symlink_is_not_followed(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        target = Path(self.cache_tmp.name) / 'cache-target'
        target.mkdir()
        link = Path(self.cache_tmp.name) / 'annotations-link'
        link.symlink_to(target, target_is_directory=True)
        result = metrics.scan(self.root,
                              annotations=self.annotate([self.claim(role='auxiliary',
                                                                   requiredness='optional')]),
                              cache_dir=link)
        enrichment = result['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'file')
        self.assertIn('cache_directory_symlink', enrichment['notes'])
        self.assertEqual(list(target.iterdir()), [])

    def test_cache_file_symlink_is_not_read(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        digest = metrics.scan(self.root)['content_digest']
        sentinel = Path(self.cache_tmp.name) / 'sentinel.json'
        sentinel.write_text('{"sentinel": true}')
        self.cache.mkdir(mode=0o700)
        (self.cache / (digest + '.json')).symlink_to(sentinel)
        enrichment = metrics.scan(self.root,
                                  cache_dir=self.cache)['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'absent')
        self.assertIn('cache_unreadable', enrichment['notes'])
        self.assertEqual(sentinel.read_text(), '{"sentinel": true}')

    def test_existing_loose_cache_dir_is_refused_without_chmod(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        self.cache.mkdir(parents=True)
        os.chmod(self.cache, 0o755)
        result = metrics.scan(self.root,
                              annotations=self.annotate([self.claim(role='auxiliary',
                                                                   requiredness='optional')]),
                              cache_dir=self.cache)
        enrichment = result['assessment']['facts']['enrichment']
        self.assertEqual(enrichment['source'], 'file')
        self.assertIn('cache_directory_insecure_permissions', enrichment['notes'])
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o755)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_cache_creation_does_not_chmod_existing_parents(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        parent = Path(self.cache_tmp.name) / 'parent'
        parent.mkdir()
        os.chmod(parent, 0o755)
        cache = parent / 'annotations'
        metrics.scan(self.root,
                     annotations=self.annotate([self.claim(role='auxiliary',
                                                          requiredness='optional')]),
                     cache_dir=cache)
        self.assertEqual(parent.stat().st_mode & 0o777, 0o755)
        self.assertEqual(cache.stat().st_mode & 0o777, 0o700)

    def test_same_content_different_path_reuses_cache(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        claim = self.claim(role='auxiliary', requiredness='optional')
        digest = metrics.scan(self.root, annotations=self.annotate([claim]),
                              cache_dir=self.cache)['content_digest']
        copy_root = Path(self.cache_tmp.name) / 'copy-plugin'
        shutil.copytree(self.root, copy_root)
        reused = metrics.scan(copy_root, cache_dir=self.cache)
        self.assertEqual(reused['content_digest'], digest)
        self.assertEqual(reused['assessment']['facts']['enrichment']['source'], 'cache')

    def test_annotation_invalid_evidence_is_rejected(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        for claim, reason in ((self.claim(excerpt='not present'), 'excerpt_not_verbatim'),
                              (self.claim(file='../outside.md'), 'citation_outside_root_or_unread'),
                              (self.claim(file='/etc/passwd'), 'citation_outside_root')):
            with self.subTest(reason=reason):
                result = metrics.scan(self.root, annotations=self.annotate([claim]))
                self.assertEqual(result['status'], 'partial')
                self.assertEqual(result['assessment']['rule'], 'INCOMPLETE_EVIDENCE')
                self.assertEqual(result['assessment']['facts']['enrichment']['status'], 'invalid')
                self.assertTrue(any(gap['reason'] == reason
                                    for gap in result['assessment']['facts']['coverage_gaps']))

    def test_annotation_absence_and_missing_file_keep_static_policy(self):
        self.write('skills/a/SKILL.md', 'Engine is mentioned.\n')
        self.assertEqual(metrics.scan(self.root)['assessment']['rule'],
                         'INSTRUCTIONS_NO_DETECTED_BLOCKER')
        absent = self.annotate([], name='another-plugin')
        self.assertEqual(metrics.scan(self.root, annotations=absent)['assessment']['rule'],
                         'INSTRUCTIONS_NO_DETECTED_BLOCKER')
        missing = metrics.load_annotations(self.root / 'absent.json')
        result = metrics.scan(self.root, annotations=missing)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['assessment']['rule'], 'INCOMPLETE_EVIDENCE')

    def test_unread_instruction_is_coverage_gap(self):
        self.write('skills/a/SKILL.md', 'Compare claims.')
        self.write('skills/b/SKILL.md', 'x' * 300)
        assessment = metrics.scan(self.root, max_bytes=100)['assessment']
        self.assertEqual(assessment['decision'], 'needs_review')
        self.assertEqual(assessment['rule'], 'INCOMPLETE_EVIDENCE')
        self.assertTrue(assessment['facts']['coverage_gaps'])

    def test_evaluation_catalog_not_runtime(self):
        self.write('skills/a/SKILL.md', 'Compare the arguments. Explain the tradeoffs.')
        self.write('mcp-configs/catalog.json', '{"mcpServers":{"example":{}}}')
        self.write('.mcp.json', '{"mcpServers":{"disabled":{}}}')
        self.write('.claude-plugin/plugin.json', '{"name":"x","mcpServers":{}}')
        self.assertEqual(metrics.scan(self.root)['assessment']['decision'], 'eligible')
        self.write('.claude-plugin/plugin.json', '{"name":"x"}')
        self.assertEqual(metrics.scan(self.root)['assessment']['rule'], 'MCP_RUNTIME')

    def test_evaluation_mod_and_helper(self):
        self.write('skills/a/SKILL.md', 'Run scripts/helper.py to count words.')
        self.assertEqual(metrics.scan(self.root)['assessment']['decision'], 'eligible')
        self.write('hooks/hooks.json', '{"modules":["./register.tsx"]}')
        self.write('hooks/register.tsx', 'export default {}')
        self.assertEqual(metrics.scan(self.root)['assessment']['rule'], 'MOD_RUNTIME')

    def test_declared_entries_and_non_instruction_asset(self):
        self.write('.claude-plugin/plugin.json', '{"name":"x","skills":"./custom"}')
        self.write('custom/a/SKILL.md', 'Compare arguments.')
        self.write('custom/a/assets/image.bin', 'binary')
        self.assertEqual(metrics.scan(self.root)['assessment']['decision'], 'eligible')

    def test_unknown_runtime_surfaces_never_clear(self):
        self.write('skills/a/SKILL.md', 'Compare arguments.')
        for field, value in [('mcpServers', True), ('hooks', {'modules': ['custom.tsx']}), ('lspServers', {'server': {}}), ('types', 'custom.ts')]:
            self.write('.claude-plugin/plugin.json', json.dumps({'name': 'x', field: value}))
            self.assertEqual(metrics.scan(self.root)['assessment']['decision'], 'needs_review')

    def test_cli_partial_exit(self):
        self.write('bad.json', '{')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = metrics.main([str(self.root), '--no-cache'])
        self.assertEqual(code, 2)
        self.assertEqual(len(json.loads(out.getvalue())['plugins']), 1)


if __name__ == '__main__':
    unittest.main()
