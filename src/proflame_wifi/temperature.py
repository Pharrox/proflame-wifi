"""
Helper for interacting with temperatures in a flexible way.
"""
from typing import Any, Self

from .strings import BAD_ADDITION, BAD_SUBTRACTION


class Temperature:
    """
    Helper class for interacting with temperature values.
    """

    @staticmethod
    def celcius(value: float) -> Self:
        """
        Create temperature from Celcius value.

        :param value: A temperature value in Celcius.
        :type value: float
        :return: A temperature object representing the given value.
        :rtype: Temperature
        """
        return Temperature(value)

    @staticmethod
    def fahrenheit(value: float) -> Self:
        """
        Create temperature from Fahrenheit value.

        :param value: A temperature value in Fahrenheit.
        :type value: float
        :return: A temperature object representing the given value.
        :rtype: Temperature
        """
        return Temperature((value - 32) * 5/9)

    def __init__(self, celcius: float) -> None:
        """
        Create new instance of the Temperature class.

        Do not call this directly. Use the methods `Temperature.celcius` and
        `Temperature.fahrenheit` to create new instances of the class.

        :param celcius: A temperature value in Celcius.
        :type celcius: int
        """
        self._value = celcius

    def __add__(self, other: Self) -> Self:
        """
        Perform addition on two temperature objects.

        :param other: The other object to add to this temperature object.
        :type other: Temperature
        :return: A new temperature object that represents the result of the
        addition operation.
        :rtype: Temperature
        """
        if not isinstance(other, Temperature):
            raise ValueError(BAD_ADDITION % (self.__class__.__name__, other.__class__.__name__))
        return Temperature.celcius(self.to_celcius() + other.to_celcius())
    
    def __eq__(self, other: Any) -> bool:
        """
        Test equality between this and another object.

        :param other: The other object to test equality with.
        :type other: Any
        :return: Boolean value indicating whether the two objects are equal.
        :rtype: bool
        """
        if isinstance(other, Temperature):
            return self.to_celcius() == other.to_celcius()
        return False

    def __sub__(self, other: Self) -> Self:
        """
        Perform subtraction on two temperature objects.

        :param other: The other object to subtract from this temperature
        object.
        :type other: Temperature
        :return: A new temperature object that represents the result of the
        subtraction operation.
        :rtype: Temperature
        """
        if not isinstance(other, Temperature):
            raise ValueError(BAD_SUBTRACTION % (self.__class__.__name__, other.__class__.__name__))
        return Temperature.celcius(self.to_celcius() - other.to_celcius())

    def to_celcius(self) -> float:
        """
        Return the temperature value as Celcius.

        :return: The value of this temperature in Celcius.
        :rtype float:
        """
        return self._value

    def to_fahrenheit(self) -> float:
        """
        Return the temperature value as Fahrenheit.

        :return: The value of this temperature in Fahrenheit.
        :rtype float:
        """
        return (self._value * 9/5) + 32
