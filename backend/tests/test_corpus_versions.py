"""Corpus integrity, publication and rollback tests; synthetic text, no paid calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from providers.corpus_versions import (BASELINE, digest, rows, manifest, guard,
    guarded_collection, read_report, report_path, database_path, stage_repair, retrieve_evidence, activate,
    compare_citations)


class Collection:
    def __init__(self, name, metadata=None):
        self.name, self.metadata = name, metadata
        self.data = {}

    def add(self, ids, documents, metadatas, embeddings=None):
        for i, ident in enumerate(ids):
            if ident in self.data:
                raise ValueError('duplicate')
            self.data[ident] = (documents[i], metadatas[i], embeddings[i] if embeddings else [.2, .8])

    def get(self, **kwargs):
        return {'ids': list(self.data), 'documents': [r[0] for r in self.data.values()],
                'metadatas': [r[1] for r in self.data.values()],
                'embeddings': [r[2] for r in self.data.values()]}

    def query(self, **kwargs):
        values = self.get()
        return {'ids': [values['ids']], 'documents': [values['documents']],
                'metadatas': [values['metadatas']], 'distances': [[.2, .7][:len(self.data)]]}


class Client:
    def __init__(self): self.collections = {}
    def create_collection(self, name, metadata=None, **kwargs):
        if name in self.collections: raise ValueError('exists')
        self.collections[name] = Collection(name, metadata)
        return self.collections[name]
    def get_collection(self, name, **kwargs): return self.collections[name]


class CorpusVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.client = Client()
        self.parent = self.client.create_collection(BASELINE)
        meta = {'source': 'manual', 'source_sha256': 'a'*64, 'source_commit': 'rev'}
        self.parent.add(['old'], ['Calibration is required.'], [meta], [[.25, .75]])
        self.report = {'collection': BASELINE, 'records': 1, 'fingerprint': 'b'*64}
        self.old_report = json.dumps(self.report)
        (self.root/'ingestion-report.json').write_text(self.old_report)
        self.pins = {BASELINE: manifest(self.report, self.parent.get())}
        self.version_clients = {}

    def factory(self, path):
        return self.version_clients.setdefault(str(path), Client())

    def stage(self, **changes):
        kwargs = dict(client=self.client, root=self.root, embed=None,
                      text='Synthetic human test passage about paper position.',
                      source='sm-wiki/page', revision='wiki-revision-1', reviewer='test-reviewer',
                      pins=self.pins, client_factory=self.factory)
        return stage_repair(**{**kwargs, **changes})

    def test_original_pin_matches_captured_private_snapshot(self):
        # No private archive dependency: public pinned counts and digest shapes only.
        from providers.corpus_versions import load_pins
        pin = load_pins()[BASELINE]
        self.assertEqual(pin['records'], 38)
        self.assertEqual(pin['fingerprint'], '2ca5f2f1522670499b24eef33bdcdc4ef6a3c6300bbd4e937e744b2e056df5d1')
        self.assertEqual(len(pin['snapshot_sha256']), 64)

    def test_text_metadata_embedding_and_count_tampering_fail_closed(self):
        for field, replacement in [('documents', ['changed']), ('metadatas', [{'source': 'fake'}]),
                                   ('embeddings', [[.5, .5]]), ('ids', ['different'])]:
            snap = copy.deepcopy(self.parent.get()); snap[field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                guard(BASELINE, self.report, snap, self.pins)
        report = {**self.report, 'records': 2}
        with self.assertRaises(ValueError): guard(BASELINE, report, self.parent.get(), self.pins)

    def test_report_change_and_unreviewed_version_rejected(self):
        with self.assertRaises(ValueError):
            guard(BASELINE, {**self.report, 'fingerprint': 'c'*64}, self.parent.get(), self.pins)
        with self.assertRaises(ValueError): guard('invented', self.report, self.parent.get(), self.pins)

    def test_stage_clones_vectors_leaves_baseline_and_selector_untouched(self):
        before = copy.deepcopy(self.parent.get())
        result = self.stage()
        pin = result['candidate_pin']; name = pin['collection']
        self.assertEqual(pin['records'], 2)
        self.assertFalse(result['active_changed'])
        self.assertTrue(result['review_required'])
        self.assertEqual(self.parent.get(), before)
        self.assertEqual((self.root/'ingestion-report.json').read_text(), self.old_report)
        self.assertNotEqual(database_path(self.root, BASELINE), database_path(self.root, name))
        self.assertEqual(set(self.client.collections), {BASELINE})
        with self.assertRaises(ValueError):
            guarded_collection(self.factory(database_path(self.root, name)), name, self.root, None, self.pins)

    def test_reviewed_pin_allows_new_version_and_baseline_rollback(self):
        result = self.stage(); pin = result['candidate_pin']; name = pin['collection']
        approved = {**self.pins, name: pin}
        coll = guarded_collection(self.factory(database_path(self.root, name)), name, self.root, None, approved)
        self.assertEqual(len(coll.data), 2)
        baseline = guarded_collection(self.client, BASELINE, self.root, None, approved)
        self.assertEqual(len(baseline.data), 1)

    def test_activation_failure_preserves_prior_selection_and_rollback_validates(self):
        class Store:
            active = BASELINE
            def put(self, key, value): self.active = value
        store = Store()
        result = self.stage(); pin = result['candidate_pin']; name = pin['collection']
        client = self.factory(database_path(self.root, name))
        with self.assertRaises(ValueError):
            activate(client, self.root, None, {'collection': name, 'pin': pin}, store, self.pins)
        self.assertEqual(store.active, BASELINE)
        approved = {**self.pins, name: pin}
        activate(client, self.root, None, {'collection': name, 'pin': pin}, store, approved)
        self.assertEqual(store.active, name)
        client.get_collection(name).data.pop('old')
        with self.assertRaises(ValueError):
            activate(client, self.root, None, {'collection': name, 'pin': pin}, store, approved)
        # Old version is still present and its complete original pin is checked.
        activate(self.client, self.root, None, {'collection': BASELINE, 'pin': self.pins[BASELINE]}, store, approved)
        self.assertEqual(store.active, BASELINE)

    def test_rerun_is_read_only_and_same_revision_same_collection(self):
        first = self.stage(); before = copy.deepcopy(self.parent.get())
        self.assertEqual(first, self.stage())
        self.assertEqual(self.parent.get(), before)
        self.assertNotEqual(first['candidate_pin']['collection'], self.stage(revision='wiki-revision-2')['candidate_pin']['collection'])

    def test_failed_stage_does_not_activate_or_overwrite_incomplete_version(self):
        result = self.stage(); name = result['candidate_pin']['collection']
        report_path(self.root, name).unlink()
        with self.assertRaisesRegex(ValueError, 'incomplete_version'):
            self.stage()
        self.assertEqual(len(self.parent.data), 1)

    def test_staged_tamper_is_rejected_instead_of_upserted(self):
        result = self.stage(); name = result['candidate_pin']['collection']
        coll = self.factory(database_path(self.root, name)).get_collection(name)
        coll.data['old'] = ('tampered', {}, [.1, .9])
        with self.assertRaisesRegex(ValueError, 'staged_version_changed'):
            self.stage()
        self.assertEqual(self.parent.data['old'][0], 'Calibration is required.')

    def test_top_chunk_and_runners_remain_full_auditable_stored_text(self):
        result = self.stage(); name = result['candidate_pin']['collection']
        coll = self.factory(database_path(self.root, name)).get_collection(name)
        evidence = retrieve_evidence(coll, 'question', 'frame')
        self.assertEqual(len(evidence['chunks']), 1)
        self.assertEqual(len(evidence['runners_up']), 1)
        self.assertEqual(evidence['context'], evidence['chunks'][0]['text'])
        self.assertEqual(evidence['chunks'][0]['distance'], .2)
        self.assertNotIn('verdict', evidence)

    def test_empty_or_unreviewed_export_rejected(self):
        for kwargs in ({'text': ''}, {'reviewer': ''}, {'revision': ''}, {'text': 'x'*6001}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): self.stage(**kwargs)

    def test_film_comparison_reports_unchanged_evidence_honestly(self):
        before = {'question': 'exact question', 'collection': 'old',
                  'ranked': [{'id': 'old', 'text': 'original text', 'distance': .9}]}
        after = {'question': 'exact question', 'collection': 'new',
                 'chunks': [{'id': 'old', 'text': 'original text', 'distance': .9}]}
        self.assertFalse(compare_citations(before, after)['cited_chunk_changed'])
        after['chunks'] = [{'id': 'new', 'text': 'new text', 'distance': .2}]
        self.assertTrue(compare_citations(before, after)['cited_chunk_changed'])
        after['question'] = 'changed wording'
        with self.assertRaises(ValueError): compare_citations(before, after)


if __name__ == '__main__': unittest.main()
