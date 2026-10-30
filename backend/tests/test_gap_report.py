"""Gap reports: shaping, fail-closed secrets, SM forward contract."""
import io
import json
import unittest

import gap_report


CHUNK = '8135308218c2c50dfd8b0aec8c0a48b25782d42098b2af9d4aa03fb2d71ccbb6'
ANSWER = ('NOT COVERED: No manual passage within the coverage threshold '
          '(d=0.820>0.760; 8 covered max 0.741). Verify in the manual. '
          'top=' + CHUNK)
QUESTION = 'what to do if the paper is in the wrong position'


class FakeResponse:
    def __init__(self, status=201, body=b'{"ok": true}'):
        self.status = status
        self._body = body

    def read(self, n=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def post_201(request):
    assert request.full_url == gap_report.SM_FEEDBACK_URL
    assert request.get_header('Content-type') == 'application/json'
    auth = request.get_header('Authorization')
    assert auth == 'Bearer test-token', auth
    body = json.loads(request.data.decode())
    assert body['collectionId'] == 'robot-ross-atf', body
    assert body['model'] == 'afl-live'
    assert body['persona'] == 'field-engineer'
    assert body['retrievedChunkIds'] == [CHUNK]
    return FakeResponse(201)


class GapReportTests(unittest.TestCase):
    def test_happy_path_posts_shaped_payload(self):
        ok, error = gap_report.report_gap(
            QUESTION, ANSWER, [CHUNK], 0.8199027180671692,
            post=lambda req: post_201(req), token='test-token')
        self.assertTrue(ok)
        self.assertEqual(error, '')

    def test_rejects_non_covered_answer(self):
        ok, error = gap_report.report_gap(
            QUESTION, 'WORLD CHECK FAILED: no paper.',
            [CHUNK], 0.5, post=post_201, token='test-token')
        self.assertFalse(ok)
        self.assertEqual(error, 'not_a_coverage_refusal')

    def test_rejects_bad_chunk_ids(self):
        for bad in ([], ['short'], ['x' * 64], 'not-a-list'):
            ok, error = gap_report.report_gap(
                QUESTION, ANSWER, bad, 0.5, post=post_201, token='test-token')
            self.assertFalse(ok, bad)
            self.assertEqual(error, 'bad_chunk_ids')

    def test_rejects_bad_distance(self):
        for bad in ('0.8', float('nan'), -1, 10):
            ok, error = gap_report.report_gap(
                QUESTION, ANSWER, [CHUNK], bad, post=post_201, token='test-token')
            self.assertFalse(ok, bad)

    def test_sm_non_201_is_short_code(self):
        ok, error = gap_report.report_gap(
            QUESTION, ANSWER, [CHUNK], 0.82,
            post=lambda req: FakeResponse(500, b'server blew up'),
            token='test-token')
        self.assertFalse(ok)
        self.assertEqual(error, 'sm_rejected')

    def test_sm_unreachable_is_short_code(self):
        def boom(req):
            raise ConnectionError('dns exploded verbosely')
        ok, error = gap_report.report_gap(
            QUESTION, ANSWER, [CHUNK], 0.82, post=boom, token='test-token')
        self.assertFalse(ok)
        self.assertEqual(error, 'sm_unreachable')

    def test_missing_credential_fail_closed(self):
        from unittest import mock
        with mock.patch.object(
                gap_report, 'credential',
                side_effect=gap_report.GapReportError('credential_unavailable')):
            ok, error = gap_report.report_gap(
                QUESTION, ANSWER, [CHUNK], 0.82,
                post=post_201, token=None)
        self.assertFalse(ok)
        self.assertEqual(error, 'credential_unavailable')

    def test_comment_optional_and_bounded(self):
        ok, _ = gap_report.report_gap(
            QUESTION, ANSWER, [CHUNK], 0.82, None,
            post=post_201, token='test-token')
        self.assertTrue(ok)
        ok, error = gap_report.report_gap(
            QUESTION, ANSWER, [CHUNK], 0.82, 'x' * 501,
            post=post_201, token='test-token')
        self.assertFalse(ok)
        self.assertEqual(error, 'bad_comment')


if __name__ == '__main__':
    unittest.main()
