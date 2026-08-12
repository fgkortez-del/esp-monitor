"""
Базовые исключения проекта.
"""

from __future__ import annotations


class EspMonitorError(Exception):
    """
    Базовый класс всех исключений проекта.

    Все собственные исключения должны наследоваться от него.
    """

    pass