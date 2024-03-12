import unittest

from proflame_wifi.temperature import Temperature
from proflame_wifi.strings import BAD_ADDITION, BAD_SUBTRACTION


class TemperatureTest(unittest.TestCase):

    def test_c_to_f(self):
        temp: Temperature = Temperature.celcius(0)
        self.assertEqual(temp.to_celcius(), 0)
        self.assertEqual(temp.to_fahrenheit(), 32)

    def test_f_to_c(self):
        temp: Temperature = Temperature.fahrenheit(32)
        self.assertEqual(temp.to_celcius(), 0)
        self.assertEqual(temp.to_fahrenheit(), 32)
    
    def test_addition(self):
        self.assertEqual(Temperature.celcius(15) + Temperature.celcius(5), Temperature.celcius(20))
        self.assertNotEqual(Temperature.celcius(15) + Temperature.celcius(5), Temperature.fahrenheit(20))
    
    def test_addition_error(self):
        msg = BAD_ADDITION % (Temperature.__name__, int.__name__)
        self.assertRaisesRegex(ValueError, msg, lambda: Temperature.celcius(15) + 5)
    
    def test_equality(self):
        self.assertEqual(Temperature.fahrenheit(68), Temperature.celcius(20))
        self.assertNotEqual(Temperature.fahrenheit(68), Temperature.celcius(68))
        self.assertNotEqual(Temperature.fahrenheit(68), 68)
    
    def test_subtraction(self):
        self.assertEqual(Temperature.celcius(15) - Temperature.celcius(5), Temperature.celcius(10))
        self.assertNotEqual(Temperature.celcius(15) - Temperature.celcius(5), Temperature.fahrenheit(10))
    
    def test_subtraction_error(self):
        msg = BAD_SUBTRACTION % (Temperature.__name__, int.__name__)
        self.assertRaisesRegex(ValueError, msg, lambda: Temperature.celcius(15) - 5)


if __name__ == '__main__':
    unittest.main()
