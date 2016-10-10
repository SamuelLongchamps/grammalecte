import unittest

from grammalecte_frontend.core.client import *


class ClientTests(unittest.TestCase):
    def test_empty(self):
        res = correct("")
        self.assertEqual(0, len(res))

    def test_single_sentence(self):
        res = correct("Je suis grands.")
        self.assertEqual(1, len(res))
        self.assertEqual(1, len(res[0][KEY_GRAMMAR_ERROR]))

