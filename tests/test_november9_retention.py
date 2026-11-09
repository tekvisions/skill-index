"""Offline regression for the protected DeusData URL absent on November 9."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

import public_assets
import url_lifecycle

ROOT = Path(url_lifecycle.__file__).resolve().parent
SLUG = 'deusdata-codebase-memory-mcp'
CANONICAL = 'https://skill.kymatalabs.com/p/' + SLUG + '/'
SOURCE_COMMIT = '8bf489edae65779aa2ee65f94b09066c43e2d30e'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class November9RetentionTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory).resolve()
        rules = json.loads((ROOT / 'url.lifecycle').read_text())
        protected = set(rules['captured_public_urls']) | set(rules.get('planned_release_urls', []))
        self.assertIn(CANONICAL, protected)
        (root / 'url.lifecycle').write_text(json.dumps(rules))
        (root / 'data.json').write_text('{"items":[]}')
        (root / 'sitemap.xml').write_text(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
            ''.join('<url><loc>' + u + '</loc></url>' for u in sorted(protected - {CANONICAL})) +
            '</urlset>')
        return root, rules

    def test_reported_removal_blocks_without_decision_then_retains_dated_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules = self.fixture(directory)
            baseline = copy.deepcopy(rules)
            baseline['retained_references'] = [e for e in baseline['retained_references'] if e['slug'] != SLUG]
            (root / 'url.lifecycle').write_text(json.dumps(baseline))
            url_lifecycle.render_retained(root)
            with self.assertRaisesRegex(ValueError, SLUG):
                url_lifecycle.verify(root)
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            url_lifecycle.render_retained(root)
            self.assertEqual(url_lifecycle.verify(root)['explicitly_retired'], [])
            self.assertIn(CANONICAL, url_lifecycle.urls(root))
            body = (root / 'p' / SLUG / 'index.html').read_text()
            self.assertIn('outside the current ranked discovery snapshot', body)
            self.assertIn('rel="canonical" href="' + CANONICAL + '"', body)
            self.assertIn('2026-11-07T15:24:40.076432+00:00', body)
            self.assertIn('2026-11-09', body)
            self.assertIn('/blob/' + SOURCE_COMMIT + '/README.md', body)
            self.assertNotIn('index rank', body)
            self.assertNotIn('class="rk"', body)
            schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)[1])
            self.assertEqual(schema['@type'], 'SoftwareSourceCode')
            self.assertEqual(schema['url'], CANONICAL)
            self.assertEqual(schema['codeRepository'], 'https://github.com/DeusData/codebase-memory-mcp')
            self.assertNotIn('aggregateRating', schema)

    def test_guard_protected_urls_and_all_previous_decisions_are_unchanged(self):
        rules = json.loads((ROOT / 'url.lifecycle').read_text())
        expected = json.loads((ROOT / 'tests/fixtures/retention-additions-20261109.json').read_text())
        self.assertEqual(digest({k: v for k, v in rules.items() if k != 'retained_references'}), expected['unchanged_policy_sha256'])
        count = expected['previous_reference_count']
        self.assertEqual(digest(rules['retained_references'][:count]), expected['previous_references_sha256'])
        self.assertEqual(rules['retained_references'][count:count + len(expected['entries'])], expected['entries'])
        self.assertEqual(len({e['slug'] for e in rules['retained_references']}), len(rules['retained_references']))
        self.assertEqual(hashlib.sha256((ROOT / 'url_lifecycle.py').read_bytes()).hexdigest(), expected['guard_sha256'])

    def test_source_is_pinned_and_dated(self):
        rules = json.loads((ROOT / 'url.lifecycle').read_text())
        entries = [e for e in rules['retained_references'] if e['slug'] == SLUG]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry['reviewed_on'], '2026-11-09')
        source = entry['primary_sources'][0]
        self.assertEqual(source['commit_sha'], SOURCE_COMMIT)
        self.assertEqual(source['blob_sha'], 'f3bdffe8acecc94d1dd077707a9c93b7e73b152b')
        self.assertEqual(source['evidence_sha256'], '2ca7d805b194b3f99e06311e6b2ea26a4323d9c10a430adadc547bb6f345c7cf')
        self.assertIn('/blob/' + SOURCE_COMMIT + '/README.md', source['url'])

    def test_unreviewed_removal_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules = self.fixture(directory)
            unknown = 'https://skill.kymatalabs.com/p/unreviewed-november9-removal/'
            rules['captured_public_urls'].append(unknown)
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            url_lifecycle.render_retained(root)
            with self.assertRaisesRegex(ValueError, 'unreviewed-november9-removal'):
                url_lifecycle.verify(root)

    def test_reentry_stays_owned_by_current_ranked_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self.fixture(directory)
            (root / 'data.json').write_text(json.dumps({'items': [{'slug': SLUG}]}))
            target = root / 'p' / SLUG / 'index.html'
            target.parent.mkdir(parents=True)
            target.write_text('fresh ranked generator output')
            url_lifecycle.render_retained(root)
            self.assertEqual(target.read_text(), 'fresh ranked generator output')

    def test_retained_route_is_in_public_deploy_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules = self.fixture(directory)
            (root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')
            rules['captured_public_urls'] = [CANONICAL]
            rules['planned_release_urls'] = []
            rules['retained_references'] = [e for e in rules['retained_references'] if e['slug'] == SLUG]
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            (root / 'public.assets').write_text(json.dumps({'host': rules['host'], 'root_files': [], 'legacy_source_paths': []}))
            url_lifecycle.render_retained(root)
            public_assets.seal(root)
            self.assertIn('p/' + SLUG + '/index.html', public_assets.collect_public_files(root))


if __name__ == '__main__':
    unittest.main()
