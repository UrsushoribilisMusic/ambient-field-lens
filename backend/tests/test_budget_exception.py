"""Budget ceiling exception: one human-authorized extra window."""
import json
import tempfile
import unittest
from pathlib import Path

from recal.budget import (authorize_extra_usd, reserve_window,
                          CEILING_USD, WINDOW_RESERVE_USD)


def fresh_ledger(extra_windows=0):
    tmp = Path(tempfile.mkdtemp()) / 'budget.json'
    tmp.write_text(json.dumps(
        {'ceiling_usd': CEILING_USD, 'cpu_and_build_reserve_usd': 2.0,
         'windows': [{'id': 'w%d' % i, 'reserved_usd': WINDOW_RESERVE_USD}
                     for i in range(extra_windows)]}))
    return tmp


class BudgetExceptionTests(unittest.TestCase):
    def test_ceiling_still_blocks_without_exception(self):
        path = fresh_ledger(extra_windows=24)  # 2 + 96 = 98, +4 > 100
        with self.assertRaises(ValueError):
            reserve_window(path)

    def test_authorized_extra_permits_exactly_one_more(self):
        path = fresh_ledger(extra_windows=24)
        total = authorize_extra_usd(path, 4.0, {
            'by': 'test', 'evidence': 'test', 'purpose': 'test'})
        self.assertEqual(total, 4.0)
        item = reserve_window(path)  # 25th fits: 102 <= 104
        self.assertTrue(item['id'])
        with self.assertRaises(ValueError):  # 26th does not
            reserve_window(path)

    def test_exception_needs_size_and_name(self):
        path = fresh_ledger()
        with self.assertRaises(ValueError):
            authorize_extra_usd(path, 3.0, {'by': 'x'})
        with self.assertRaises(ValueError):
            authorize_extra_usd(path, 4.0, {'evidence': 'x'})
        with self.assertRaises(ValueError):
            authorize_extra_usd(path, -4.0, {'by': 'x'})

    def test_malformed_extra_rejected(self):
        path = fresh_ledger()
        ledger = json.loads(path.read_text())
        ledger['authorized_extra_usd'] = 'plenty'
        path.write_text(json.dumps(ledger))
        with self.assertRaises(ValueError):
            reserve_window(path)


if __name__ == '__main__':
    unittest.main()
