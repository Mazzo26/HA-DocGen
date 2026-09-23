"""Read-only Home Assistant ``.storage`` discovery.

Discovers filesystem metadata only. Registry parsing belongs in later
modules and must not live in this package.
"""

from __future__ import annotations

from .inventory import StorageInventory
from .models import StorageFile
from .scanner import StorageScanner

__all__ = [
    "StorageFile",
    "StorageInventory",
    "StorageScanner",
]
