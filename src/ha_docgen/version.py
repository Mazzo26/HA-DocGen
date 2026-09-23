"""Authoritative version information for HA-DocGen.

The application version is defined only here. Package metadata, the CLI
and runtime diagnostics all read this module. Discovery never uses Git.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

APP_NAME: Final[str] = "HA-DocGen"
VERSION: Final[str] = "0.2.0"

_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class InvalidVersionError(ValueError):
    """Raised when a version string is not a valid semantic version."""


@dataclass(frozen=True, slots=True)
class SemanticVersion:
    """Parsed semantic version (MAJOR.MINOR.PATCH[-prerelease][+build])."""

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    def __str__(self) -> str:
        """Return the canonical semantic version string."""
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is not None:
            value = f"{value}-{self.prerelease}"
        if self.build is not None:
            value = f"{value}+{self.build}"
        return value


def validate_version(value: str) -> str:
    """Return ``value`` when it is a valid semantic version."""
    parse_version(value)
    return value


def parse_version(value: str) -> SemanticVersion:
    """Parse a semantic version string into an immutable value object."""
    match = _SEMVER_PATTERN.fullmatch(value)
    if match is None:
        raise InvalidVersionError(f"Invalid semantic version: {value}")
    return SemanticVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=match.group("prerelease"),
        build=match.group("build"),
    )


def get_version() -> str:
    """Return the authoritative application version."""
    return VERSION


__version__ = VERSION
validate_version(VERSION)
