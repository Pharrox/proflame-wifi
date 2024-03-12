"""
Helper functions used throughout the module.
"""

def constrain(value: int, min_value: int, max_value: int):
    """
    Constrain a number to a specified range.

    :param value: The input value to constrain.
    :type value: int
    :param min_value: The lower bound that the output should be constrained to.
    :type min_value: int
    :param max_value: The upper bound that the output should be constrained to.
    :type max_value: int
    """
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value
