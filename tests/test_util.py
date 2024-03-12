import unittest

from proflame_wifi.util import constrain


class UtilTest(unittest.TestCase):

    def test_constrain(self):
        result = constrain(2, 1, 3)
        self.assertEqual(result, 2)

    def test_constrain_lower_bound(self):
        result = constrain(0, 1, 3)
        self.assertEqual(result, 1)

    def test_constrain_upper_bound(self):
        result = constrain(5, 1, 3)
        self.assertEqual(result, 3)


if __name__ == '__main__':
    unittest.main()
