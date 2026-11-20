"""Discovery source filters and approval/display contracts."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import discover_plugins as discover


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'home'
        self.state = self.base / 'state'
        self.installations = {}

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data) if not isinstance(data, str) else data)

    def plugin(self, name, text='Compare database queries and SQL performance.'):
        root = self.base / name
        self.write(root / '.claude-plugin/plugin.json', {'name': name, 'description': 'Database SQL query optimization'})
        self.write(root / 'skills/main/SKILL.md', text)
        self.installations[name + '@market'] = [{'installPath': str(root), 'scope': 'user', 'version': '1'}]
        self.write(self.home / 'plugins/installed_plugins.json', {'version': 2, 'plugins': self.installations})
        return root

    def test_no_state_bootstrap_and_related_pair(self):
        self.plugin('one')
        self.plugin('two')
        result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual(sum(len(g['plugins']) for g in result['groups']), 2)
        self.assertFalse(self.state.exists())
        self.assertIn('Valides-tu', discover.render(result))

    def test_singleton_removed_but_topic_anchor_kept(self):
        self.plugin('one')
        self.assertFalse(discover.discover(self.home, self.state, cache_dir=None)['groups'])
        self.write(self.state / 'registry.json', {'topics': [{'type': 'topic', 'id': 'db', 'name': 'Database SQL',
                   'short_description': 'Database SQL query optimization', 'scope': 'Database queries and SQL performance', 'items': []}], 'artifacts': []})
        result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual(len(result['groups']), 1)
        self.assertEqual(len(result['groups'][0]['topics']), 1)

    def test_custom_blacklist_persistence_and_mandatory_self(self):
        self.plugin('one')
        self.plugin('two')
        self.plugin('skill-recomposer')
        discover.blacklist(self.state, 'add', 'one@market')
        self.assertEqual(discover.blacklist(self.state), ['one@market'])
        result = discover.discover(self.home, self.state, cache_dir=None)
        reasons = {e['name']: e['reason'] for e in result['excluded']}
        self.assertEqual(reasons['one'], 'custom_blacklist')
        self.assertEqual(reasons['skill-recomposer'], 'self')
        discover.blacklist(self.state, 'remove', 'one@market')
        self.assertEqual(discover.blacklist(self.state), [])

    def test_managed_marker_and_copy_hash_excluded(self):
        first = self.plugin('one')
        second = self.plugin('two')
        self.write(first / 'skills/main/.recomposition.json', {})
        digest = hashlib.sha256((second / 'skills/main/SKILL.md').read_bytes()).hexdigest()
        self.write(self.state / 'registry.json', {'topics': [], 'artifacts': [{'path': 'elsewhere/SKILL.md', 'sha256': digest}]})
        result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertFalse(result['groups'])
        self.assertTrue(all(e['reason'] == 'managed_output' for e in result['excluded']))

    def test_keep_review_remove_ineligible_and_exhaustive(self):
        self.plugin('one')
        self.plugin('two')
        self.plugin('three')
        def fake_scan(root, identities, **kwargs):
            return {'assessment': {'decision': {'one': 'eligible', 'two': 'needs_review', 'three': 'ineligible'}[root.name], 'facts': {'entries': []}}}
        with patch.object(discover, 'scan', fake_scan):
            result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual({p['name'] for g in result['groups'] for p in g['plugins']}, {'one', 'two'})
        self.assertEqual(next(e for e in result['excluded'] if e['name'] == 'three')['reason'], 'ineligible')
        self.assertIn('À examiner', discover.render(result))

    def test_bad_blacklist_blocks_and_render_escapes(self):
        self.write(self.state / 'discover-blacklist.json', {'schema_version': 1, 'plugins': 'bad'})
        with self.assertRaises(ValueError):
            discover.blacklist(self.state)
        self.assertEqual(discover.cell('x|y\n\x1bz'), 'x\\|y  z')

    def test_uppercase_managed_hash_and_manifest_symlink(self):
        root = self.plugin('one')
        digest = hashlib.sha256((root / 'skills/main/SKILL.md').read_bytes()).hexdigest().upper()
        self.write(self.state / 'registry.json', {'topics': [], 'artifacts': [{'path': 'elsewhere', 'sha256': digest}]})
        result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual(result['excluded'][0]['reason'], 'managed_output')
        manifest = root / '.claude-plugin/plugin.json'
        manifest.unlink()
        outside = self.base / 'private.json'
        self.write(outside, {'name': 'secret'})
        manifest.symlink_to(outside)
        with self.assertRaises(ValueError):
            discover.metadata(root)

    def test_scan_failure_is_diagnostic(self):
        self.plugin('one')
        with patch.object(discover, 'scan', side_effect=OSError('unreadable')):
            result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual(result['notes'][0]['reason'], 'scan_failed')
        self.assertEqual(result['excluded'][0]['reason'], 'scan_failed')

    def test_duplicate_keys_render_exact_roots(self):
        root = self.plugin('one')
        other = self.base / 'other'
        self.write(other / '.claude-plugin/plugin.json', {'name': 'one', 'description': 'Database SQL query optimization'})
        self.write(other / 'skills/main/SKILL.md', 'Compare SQL queries.')
        self.installations['one@market'].append({'installPath': str(other), 'scope': 'project', 'version': '2'})
        self.write(self.home / 'plugins/installed_plugins.json', {'version': 2, 'plugins': self.installations})
        rendered = discover.render(discover.discover(self.home, self.state, cache_dir=None))
        self.assertIn(discover.cell(str(root)), rendered)
        self.assertIn(discover.cell(str(other)), rendered)

    def test_multiline_metadata_does_not_include_body_indentation(self):
        root = self.plugin('one', '---\nname: one\ndescription: >-\n  Database SQL optimization\n---\n# Body\n  unrelated private body content\n')
        report = {'assessment': {'facts': {'entries': ['skills/main/SKILL.md']}}}
        segments = discover.instruction_metadata(root, report)
        self.assertIn('Database SQL optimization', segments[0])
        self.assertNotIn('private body', segments[0])
        self.assertIn('one', segments)

    def test_local_names_preserve_concise_subthemes(self):
        first = self.plugin('one', '---\nname: orchard-pruning\ndescription: Extensive botanical maintenance procedures across seasons and climate zones.\n---\n')
        second = self.plugin('two', '---\nname: orchard-pruning-tools\ndescription: Specialized equipment guides for maintaining branches and trees.\n---\n')
        # No product-name taxonomy: author-supplied local identities carry the overlap.
        result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual({p['name'] for g in result['groups'] for p in g['plugins']}, {'one', 'two'})

    def test_broad_existing_topic_keeps_matching_plugin(self):
        self.plugin('one', '---\nname: quasar-lattice-telemetry\ndescription: quasar lattice telemetry mode\n---\n')
        self.write(self.state / 'registry.json', {'topics': [{'type': 'topic', 'id': 'broad', 'name': 'Operations',
            'short_description': 'Systems overview', 'scope': 'quasar lattice telemetry mode. Orchard pruning branch equipment foliage irrigation. Payroll accounting invoices billing receipts.', 'items': []}], 'artifacts': []})
        result = discover.discover(self.home, self.state, cache_dir=None)
        self.assertEqual(len(result['groups']), 1)
        self.assertTrue(result['groups'][0]['topics'])

    def test_late_description_words_reach_clustering(self):
        root = self.plugin('one', '---\nname: one\ndescription: >-\n  ' + 'alpha ' * 300 + 'cryptography\n---\n')
        segments = discover.instruction_metadata(root, {'assessment': {'facts': {'entries': ['skills/main/SKILL.md']}}})
        self.assertIn('cryptography', segments[0])

    def test_operation_has_explicit_selection_gate(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / 'operations/discover.md').read_text()
        self.assertIn('After explicit selection', text)
        self.assertIn('never ordinary', text)
        self.assertIn('No source deletion', text)
        skill = (root / 'skills/skill-recomposer/SKILL.md').read_text()
        self.assertIn('`discover` → `operations/discover.md`', skill)
        self.assertLess(skill.index('## Discovery shortcut'), skill.index('## Load the kernel'))


if __name__ == '__main__':
    unittest.main()
