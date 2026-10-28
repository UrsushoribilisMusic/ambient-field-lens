"""CPU-only fake transport; no real credentials, provider calls, or human labels."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import urllib.error
from generation import wording as w
from generation.import_meta import import_receipt


class WordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / 'api-calls.jsonl'
        self.key = 'test-only-credential-not-real'
        self.fetch = Mock(return_value=self.key)

    def response(self, **overrides):
        value = {'model': w.ROUTES['baseten'][1],
                 'usage': {'prompt_tokens': 100, 'completion_tokens': 80, 'total_tokens': 180},
                 'choices': [{'finish_reason': 'stop', 'message': {'content': 'Review this draft.'}}]}
        value.update(overrides)
        return 200, json.dumps(value).encode()

    def run_job(self, send, **kwargs):
        return w.execute('example', 'review_copy', 'Rewrite this sentence.', output_root=self.root / 'outputs',
                         ledger=self.ledger, fetch=self.fetch, send=send, **kwargs)

    def test_default_routing_and_durable_receipt_before_send(self):
        def send(endpoint, body, key):
            self.assertEqual(endpoint, w.ROUTES['baseten'][0])
            self.assertEqual(json.loads(body)['model'], 'meta-models/muse-spark-open-1026')
            self.assertTrue((self.root/'outputs/example/attempt.json').exists())
            self.assertEqual(len(self.ledger.read_text().splitlines()), 1)
            self.assertEqual(key, self.key)
            return self.response()
        result = self.run_job(send)
        self.assertEqual(result['status'], 'draft_generated_pending_human_review')
        self.assertAlmostEqual(result['estimated_api_cost_usd_uncached'], .000465)
        self.assertEqual(len(self.ledger.read_text().splitlines()), 2)
        for p in self.root.rglob('*'):
            if p.is_file():
                self.assertNotIn(self.key.encode(), p.read_bytes())
        self.assertEqual(self.fetch.call_args.args, ('baseten',))

    def test_sam_scoring_and_readouts_cannot_be_routed_here(self):
        for purpose in ('sam', 'hidden_states', 'probe', 'score', 'readout'):
            with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                w.plan('example', purpose, 'text')
        for provider in ('modal', 'sam', 'custom'):
            with self.assertRaises(ValueError):
                w.plan('example', 'step_text', 'text', provider)
        for tokens in (True, 0, 4097):
            with self.assertRaises(ValueError):
                w.plan('example', 'step_text', 'text', max_tokens=tokens)

    def test_meta_overflow_is_explicit_and_uses_same_ledger(self):
        send = Mock(return_value=self.response(model='muse-spark-1.3'))
        result = self.run_job(send, provider='meta')
        self.assertEqual(send.call_args.args[0], w.ROUTES['meta'][0])
        self.assertEqual(result['provider'], 'meta')
        self.assertEqual(self.fetch.call_args.args, ('meta',))

    def test_http_failure_has_no_retry_no_fallback_or_error_text(self):
        error = urllib.error.HTTPError('https://example.invalid', 429, self.key, {}, None)
        send = Mock(side_effect=error)
        result = self.run_job(send)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(result['status'], 'http_error_no_retry')
        self.assertIsNone(result['usage'])
        self.assertIsNone(result['estimated_api_cost_usd_uncached'])
        self.assertNotIn(self.key, self.ledger.read_text())
        with self.assertRaises(FileExistsError):
            self.run_job(send)
        self.assertEqual(send.call_count, 1)

    def test_missing_usage_truncation_empty_and_wrong_model_withhold_draft(self):
        variants = [({'usage': None}, 'usage_unknown_no_retry'),
                    ({'model': 'different-model'}, 'response_model_mismatch'),
                    ({'choices': [{'finish_reason': 'length', 'message': {'content': 'partial'}}]}, 'incomplete_no_retry'),
                    ({'choices': [{'finish_reason': 'stop', 'message': {'content': ''}}]}, 'empty_text_no_retry')]
        for index, (change, expected) in enumerate(variants):
            with self.subTest(expected=expected):
                result = w.execute(str(index), 'pair_phrasings', 'Draft wording only.',
                                   output_root=self.root, ledger=self.ledger, fetch=self.fetch,
                                   send=Mock(return_value=self.response(**change)))
                self.assertEqual(result['status'], expected)
                self.assertFalse((self.root/str(index)/'draft.txt').exists())

    def test_response_or_prompt_cannot_persist_credentials(self):
        result = self.run_job(Mock(return_value=(200, self.key.encode())))
        self.assertEqual(result['status'], 'failed_no_retry')
        self.assertFalse((self.root/'outputs/example/response.json').exists())
        for tokens in ({'prompt_tokens': True, 'completion_tokens': 1, 'total_tokens': 2},
                       {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 99}):
            self.assertEqual(w.usage_cost({'usage': tokens}, 'baseten'), (None, None))
        send = Mock()
        with self.assertRaises(ValueError):
            w.execute('leak', 'review_copy', self.key, output_root=self.root,
                      ledger=self.ledger, fetch=self.fetch, send=send)
        send.assert_not_called()

    def test_historical_import_records_known_and_unknown_cost_and_is_idempotent(self):
        for model in ('muse-spark-1.3', 'sam-3.1'):
            folder = self.root/model
            folder.mkdir()
            receipt = folder/'attempt.json'
            receipt.write_text(json.dumps({'model': model, 'attempted_at': '2026-10-27'}))
            (folder/'response.json').write_text(json.dumps({'usage': {
                'input_tokens': 100, 'output_tokens': 80, 'total_tokens': 180}}))
            self.assertTrue(import_receipt(receipt, self.ledger))
            self.assertFalse(import_receipt(receipt, self.ledger))
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]['estimated_api_cost_usd_uncached'], .000465)
        self.assertIsNone(rows[1]['estimated_api_cost_usd_uncached'])
        self.assertFalse(rows[0]['new_paid_call'])


if __name__ == '__main__':
    unittest.main()
