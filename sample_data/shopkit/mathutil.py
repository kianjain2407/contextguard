"""
Mathematical utility functions for shopkit.
"""
from typing import List, Union

def clamp(val: Union[int, float], low: Union[int, float], high: Union[int, float]) -> Union[int, float]:
    """
    Clamps a value within the specified [low, high] bounds.
    If val < low, returns low.
    If val > high, returns high.
    Otherwise returns val.
    """
    if val < low:
        return low
    if val > high:
        return high
    return val

def average(numbers: List[Union[int, float]]) -> float:
    """
    Calculates the arithmetic mean of a list of numbers.
    Bug in original: does not guard against empty list (raises ZeroDivisionError).
    """
    return sum(numbers) / len(numbers)

def percent(part: Union[int, float], whole: Union[int, float]) -> float:
    """
    Calculates the percentage of part relative to whole.
    Returns 0.0 if whole is 0.
    """
    if whole == 0:
        return 0.0
    return (part / whole) * 100.0
