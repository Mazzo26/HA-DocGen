#!/usr/bin/env python3
"""Release readiness and release-tag validation for HA-DocGen.

This script is release infrastructure only. It does not create tags,
GitHub Releases, or publish artifacts.

Modes:

- Readiness (default): pre-tag checks, including packaging and “tag absent”.
- Release (``--tag`` or a GitHub Actions tag ref): enforce
  ``tag == v{VERSION}`` and related consistency checks without rebuilding.
  The release workflow owns ``python -m build`` and ``twine check``.
"""

from __future__ import annotations

import argparse
import email.parser
import importlib.metadata
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

DISTRIBUTION_NAME = "ha-docgen"
VERSION_ATTR = "ha_docgen.version.VERSION"
DEFAULT_ALLOWED_BRANCHES = frozenset({"main", "develop"})
REQUIRED_FILES = (
    "pyproject.toml",
    "LICENSE",
    "README.md",
    "src/ha_docgen/__init__.py",
    "src/ha_docgen/version.py",
    ".github/workflows/ci.yml",
)


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one validation check."""

    name: str
    passed: bool
    detail: str


class ReleaseValidationError(RuntimeError):
    """Raised when a validation step cannot complete."""


def repository_root(start: Path | None = None) -> Path:
    """Return the repository root that contains pyproject.toml."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ReleaseValidationError(
        f"Unable to locate repository root from {current}"
    )


def resolve_application_version() -> str:
    """Return the authoritative application version from source."""
    from ha_docgen.version import VERSION, get_version, validate_version

    validate_version(VERSION)
    runtime = get_version()
    if runtime != VERSION:
        raise ReleaseValidationError(
            f"get_version() returned {runtime!r}, expected {VERSION!r}"
        )
    return VERSION


def expected_release_tag(version: str) -> str:
    """Return the Git tag name that encodes ``version``."""
    return f"v{version}"


def normalize_tag(tag: str) -> str:
    """Strip a leading ``v`` when the tag encodes a numeric version."""
    if len(tag) > 1 and tag[0] == "v" and tag[1].isdigit():
        return tag[1:]
    return tag


def detect_github_release_tag() -> str | None:
    """Return the pushed tag name when running under a GitHub tag ref."""
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        name = (os.environ.get("GITHUB_REF_NAME") or "").strip()
        return name or None
    ref = os.environ.get("GITHUB_REF") or ""
    prefix = "refs/tags/"
    if ref.startswith(prefix):
        return ref.removeprefix(prefix) or None
    return None


def check_release_tag_matches(tag: str, version: str) -> CheckResult:
    """Confirm the Git tag is exactly ``v{VERSION}``."""
    expected = expected_release_tag(version)
    if tag != expected:
        return CheckResult(
            "release tag matches VERSION",
            False,
            f"tag {tag!r} != expected {expected!r}",
        )
    return CheckResult(
        "release tag matches VERSION",
        True,
        f"{tag} == {expected}",
    )


def validate_release(tag: str, dist_dir: Path, version: str) -> None:
    """Raise ``ValueError`` when tag, package, or dist metadata disagree.

    Used by release automation after distributions exist. Prefer
    :func:`check_release_tag_matches` and the other check helpers for
    structured readiness reports.
    """
    expected = expected_release_tag(version)
    if tag != expected:
        raise ValueError(
            f"Git tag {tag!r} does not match VERSION {version!r} "
            f"(expected {expected!r})"
        )

    try:
        installed = importlib.metadata.version(DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValueError(
            f"package metadata: distribution {DISTRIBUTION_NAME!r} "
            "is not installed"
        ) from exc
    if installed != version:
        raise ValueError(
            f"package metadata {installed!r} != VERSION {version!r}"
        )

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError(
            f"expected one wheel and one sdist in {dist_dir}, "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        )

    wheel_version = read_wheel_version(wheels[0])
    if wheel_version != version:
        raise ValueError(
            f"wheel metadata {wheel_version!r} != VERSION {version!r}"
        )

    sdist_version = read_sdist_version(sdists[0])
    if sdist_version != version:
        raise ValueError(
            f"sdist metadata {sdist_version!r} != VERSION {version!r}"
        )


def read_metadata_field(text: str, name: str) -> str:
    """Return one RFC 822 metadata field value."""
    message = email.parser.Parser().parsestr(text, headersonly=True)
    value = message.get(name)
    if value is None or not str(value).strip():
        raise ReleaseValidationError(f"Missing metadata field: {name}")
    return str(value).strip()


def read_wheel_metadata(wheel: Path) -> str:
    """Return the wheel METADATA payload as text."""
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            (
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ),
            None,
        )
        if metadata_name is None:
            raise ReleaseValidationError(f"No METADATA in wheel: {wheel.name}")
        return archive.read(metadata_name).decode("utf-8")


def read_wheel_version(wheel: Path) -> str:
    """Return the Version field from a wheel METADATA file."""
    return read_metadata_field(read_wheel_metadata(wheel), "Version")


def read_sdist_pkg_info(sdist: Path) -> str:
    """Return the sdist root PKG-INFO payload as text."""
    with tarfile.open(sdist, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            parts = Path(member.name).parts
            if len(parts) == 2 and parts[1] == "PKG-INFO":
                extracted = archive.extractfile(member)
                if extracted is None:
                    break
                return extracted.read().decode("utf-8")
    raise ReleaseValidationError(f"No root PKG-INFO in sdist: {sdist.name}")


def read_sdist_version(sdist: Path) -> str:
    """Return the Version field from the sdist root PKG-INFO only."""
    return read_metadata_field(read_sdist_pkg_info(sdist), "Version")


def _run(
    command: tuple[str, ...],
    *,
    cwd: Path,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and raise on failure."""
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=capture,
        text=True,
    )
    if completed.returncode != 0:
        output = ""
        if capture:
            output = (completed.stdout or "") + (completed.stderr or "")
            output = output.strip()
        detail = output or f"exit status {completed.returncode}"
        raise ReleaseValidationError(
            f"Command failed ({' '.join(command)}): {detail}"
        )
    return completed


def _git(root: Path, *args: str) -> str:
    """Run git in the repository and return stripped stdout."""
    completed = _run(("git", *args), cwd=root)
    return (completed.stdout or "").strip()


def check_required_files(root: Path) -> CheckResult:
    """Verify packaging and release prerequisite files exist."""
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        return CheckResult(
            "required files",
            False,
            "missing: " + ", ".join(missing),
        )
    return CheckResult(
        "required files",
        True,
        f"{len(REQUIRED_FILES)} required paths present",
    )


def check_clean_working_tree(root: Path, *, allow_dirty: bool) -> CheckResult:
    """Verify the Git working tree has no uncommitted changes."""
    status = _git(root, "status", "--porcelain")
    if not status:
        return CheckResult("clean working tree", True, "no local changes")
    if allow_dirty:
        return CheckResult(
            "clean working tree",
            True,
            "dirty tree allowed by --allow-dirty",
        )
    preview = "; ".join(status.splitlines()[:5])
    return CheckResult("clean working tree", False, preview)


def check_current_branch(
    root: Path,
    *,
    allowed_branches: frozenset[str],
) -> CheckResult:
    """Verify HEAD is on an allowed branch (not detached)."""
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        return CheckResult(
            "current branch",
            False,
            "detached HEAD is not suitable for creating a release",
        )
    if branch not in allowed_branches:
        allowed = ", ".join(sorted(allowed_branches))
        return CheckResult(
            "current branch",
            False,
            f"on {branch!r}; expected one of: {allowed}",
        )
    return CheckResult("current branch", True, branch)


def check_version_resolution() -> CheckResult:
    """Resolve and validate the authoritative application version."""
    try:
        version = resolve_application_version()
    except Exception as exc:  # noqa: BLE001 - surface any resolution failure
        return CheckResult("package version", False, str(exc))
    return CheckResult("package version", True, version)


def check_pyproject_dynamic_version(root: Path, version: str) -> CheckResult:
    """Confirm pyproject.toml reads VERSION dynamically from source."""
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    dynamic = project.get("dynamic", [])
    if "version" not in dynamic:
        return CheckResult(
            "pyproject dynamic version",
            False,
            "project.dynamic does not include 'version'",
        )
    if "version" in project:
        return CheckResult(
            "pyproject dynamic version",
            False,
            "static project.version must not be set",
        )
    attr = (
        data.get("tool", {})
        .get("setuptools", {})
        .get("dynamic", {})
        .get("version", {})
        .get("attr")
    )
    if attr != VERSION_ATTR:
        return CheckResult(
            "pyproject dynamic version",
            False,
            f"expected attr {VERSION_ATTR!r}, found {attr!r}",
        )
    return CheckResult(
        "pyproject dynamic version",
        True,
        f"{VERSION_ATTR} -> {version}",
    )


def check_installed_metadata(version: str) -> CheckResult:
    """Confirm the editable/installed distribution matches VERSION."""
    try:
        installed = importlib.metadata.version(DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError:
        return CheckResult(
            "installed package metadata",
            False,
            f"distribution {DISTRIBUTION_NAME!r} is not installed",
        )
    if installed != version:
        return CheckResult(
            "installed package metadata",
            False,
            f"installed {installed!r} != VERSION {version!r}",
        )
    return CheckResult("installed package metadata", True, installed)


def check_build_and_twine(root: Path, dist_dir: Path) -> CheckResult:
    """Build distributions and run twine check."""
    if dist_dir.exists():
        for path in dist_dir.iterdir():
            if path.is_file():
                path.unlink()
    else:
        dist_dir.mkdir(parents=True, exist_ok=True)

    try:
        _run(
            (
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--wheel",
                "--outdir",
                str(dist_dir),
            ),
            cwd=root,
        )
        _run(
            (sys.executable, "-m", "twine", "check", *sorted(map(str, dist_dir.iterdir()))),
            cwd=root,
        )
    except ReleaseValidationError as exc:
        return CheckResult("packaging (build + twine)", False, str(exc))

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        return CheckResult(
            "packaging (build + twine)",
            False,
            f"expected one wheel and one sdist, found {len(wheels)} wheel(s) "
            f"and {len(sdists)} sdist(s)",
        )
    return CheckResult(
        "packaging (build + twine)",
        True,
        f"{wheels[0].name}, {sdists[0].name}",
    )


def check_distribution_metadata(dist_dir: Path, version: str) -> CheckResult:
    """Confirm built wheel and sdist metadata match VERSION."""
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        return CheckResult(
            "distribution metadata",
            False,
            "build artifacts missing; run packaging check first",
        )
    try:
        wheel_text = read_wheel_metadata(wheels[0])
        sdist_text = read_sdist_pkg_info(sdists[0])
        wheel_version = read_metadata_field(wheel_text, "Version")
        sdist_version = read_metadata_field(sdist_text, "Version")
        wheel_name = read_metadata_field(wheel_text, "Name")
        sdist_name = read_metadata_field(sdist_text, "Name")
    except ReleaseValidationError as exc:
        return CheckResult("distribution metadata", False, str(exc))

    problems: list[str] = []
    if wheel_version != version:
        problems.append(f"wheel metadata {wheel_version!r}")
    if sdist_version != version:
        problems.append(f"sdist metadata {sdist_version!r}")
    if wheel_name != DISTRIBUTION_NAME:
        problems.append(f"wheel name {wheel_name!r}")
    if sdist_name != DISTRIBUTION_NAME:
        problems.append(f"sdist name {sdist_name!r}")
    if problems:
        return CheckResult(
            "distribution metadata",
            False,
            f"mismatch vs VERSION {version!r}: " + ", ".join(problems),
        )
    return CheckResult(
        "distribution metadata",
        True,
        f"wheel and sdist Version={version}",
    )


def _local_tags(root: Path) -> set[str]:
    """Return local tag names."""
    output = _git(root, "tag", "--list")
    if not output:
        return set()
    return set(output.splitlines())


def _remote_tags(root: Path) -> set[str]:
    """Return tag names advertised by origin."""
    completed = _run(("git", "ls-remote", "--tags", "origin"), cwd=root)
    tags: set[str] = set()
    for line in (completed.stdout or "").splitlines():
        if not line.strip():
            continue
        ref = line.split()[-1]
        if ref.endswith("^{}"):
            continue
        prefix = "refs/tags/"
        if ref.startswith(prefix):
            tags.add(ref.removeprefix(prefix))
    return tags


def check_release_tag_absent(root: Path, version: str) -> CheckResult:
    """Fail when the intended release tag already exists."""
    tag = expected_release_tag(version)
    local = _local_tags(root)
    try:
        remote = _remote_tags(root)
    except ReleaseValidationError as exc:
        return CheckResult("release tag absent", False, str(exc))

    locations: list[str] = []
    if tag in local:
        locations.append("local")
    if tag in remote:
        locations.append("origin")
    if locations:
        return CheckResult(
            "release tag absent",
            False,
            f"tag {tag} already exists ({', '.join(locations)})",
        )
    return CheckResult(
        "release tag absent",
        True,
        f"{tag} not present locally or on origin",
    )


def _print_result(result: CheckResult) -> None:
    """Print one PASS/FAIL line."""
    status = "PASS" if result.passed else "FAIL"
    print(f"[{status}] {result.name}: {result.detail}")


def _dist_artifacts_present(dist_dir: Path) -> bool:
    """Return True when dist_dir already contains wheel and sdist files."""
    if not dist_dir.is_dir():
        return False
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    return bool(wheels or sdists)


def run_release_validation(
    *,
    tag: str,
    root: Path | None = None,
    allow_dirty: bool = False,
    dist_dir: Path | None = None,
) -> int:
    """Validate a pushed release tag. Return process exit status.

    Does not build distributions: the release workflow owns build and twine.
    When ``dist_dir`` already contains artifacts, their metadata is checked.
    """
    repo = repository_root(root)
    artifacts = dist_dir or (repo / "dist")

    print(f"Repository: {repo}")
    print(f"Release tag validation: {tag}")
    print("-" * 60)

    results: list[CheckResult] = []

    def record(result: CheckResult) -> CheckResult:
        results.append(result)
        _print_result(result)
        return result

    record(check_required_files(repo))
    record(check_clean_working_tree(repo, allow_dirty=allow_dirty))

    version_result = record(check_version_resolution())
    version = resolve_application_version() if version_result.passed else None

    if version is not None:
        record(check_pyproject_dynamic_version(repo, version))
        record(check_installed_metadata(version))
        record(check_release_tag_matches(tag, version))
        if _dist_artifacts_present(artifacts):
            record(check_distribution_metadata(artifacts, version))
    else:
        record(
            CheckResult(
                "pyproject dynamic version",
                False,
                "skipped: package version unresolved",
            )
        )
        record(
            CheckResult(
                "installed package metadata",
                False,
                "skipped: package version unresolved",
            )
        )
        record(
            CheckResult(
                "release tag matches VERSION",
                False,
                "skipped: package version unresolved",
            )
        )

    print("-" * 60)
    failed = [result for result in results if not result.passed]
    if failed:
        print(f"FAILED: {len(failed)} check(s) failed")
        for result in failed:
            print(f"  - {result.name}: {result.detail}", file=sys.stderr)
        return 1

    print(f"PASSED: release tag {tag} matches VERSION")
    return 0


def run_validation(
    *,
    root: Path | None = None,
    allow_dirty: bool = False,
    allowed_branches: frozenset[str] = DEFAULT_ALLOWED_BRANCHES,
    dist_dir: Path | None = None,
) -> int:
    """Run all release-readiness checks. Return process exit status."""
    repo = repository_root(root)
    artifacts = dist_dir or (repo / "dist")

    print(f"Repository: {repo}")
    print("Release validation")
    print("-" * 60)

    results: list[CheckResult] = []

    def record(result: CheckResult) -> CheckResult:
        results.append(result)
        _print_result(result)
        return result

    record(check_required_files(repo))
    record(check_clean_working_tree(repo, allow_dirty=allow_dirty))
    record(check_current_branch(repo, allowed_branches=allowed_branches))

    version_result = record(check_version_resolution())
    version = resolve_application_version() if version_result.passed else None

    if version is not None:
        record(check_pyproject_dynamic_version(repo, version))
        record(check_installed_metadata(version))
        packaging = record(check_build_and_twine(repo, artifacts))
        if packaging.passed:
            record(check_distribution_metadata(artifacts, version))
        record(check_release_tag_absent(repo, version))
    else:
        record(
            CheckResult(
                "pyproject dynamic version",
                False,
                "skipped: package version unresolved",
            )
        )
        record(
            CheckResult(
                "installed package metadata",
                False,
                "skipped: package version unresolved",
            )
        )
        record(
            CheckResult(
                "packaging (build + twine)",
                False,
                "skipped: package version unresolved",
            )
        )
        record(
            CheckResult(
                "release tag absent",
                False,
                "skipped: package version unresolved",
            )
        )

    print("-" * 60)
    failed = [result for result in results if not result.passed]
    if failed:
        print(f"FAILED: {len(failed)} check(s) failed")
        for result in failed:
            print(f"  - {result.name}: {result.detail}", file=sys.stderr)
        return 1

    print("PASSED: repository is ready for a release tag")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate HA-DocGen release readiness, or validate a pushed "
            "release tag against VERSION. Does not create GitHub Releases "
            "or publish packages."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: discover from the current directory)",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Directory for build artifacts (default: <repo>/dist)",
    )
    parser.add_argument(
        "--tag",
        default=None,
        metavar="NAME",
        help=(
            "Validate release tag NAME against VERSION (release mode). "
            "When omitted under a GitHub Actions tag ref, the pushed tag "
            "is detected automatically."
        ),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow an unclean Git working tree (local iteration only)",
    )
    parser.add_argument(
        "--allow-branch",
        action="append",
        dest="allow_branches",
        default=None,
        metavar="NAME",
        help=(
            "Branch name permitted for release readiness "
            f"(default: {', '.join(sorted(DEFAULT_ALLOWED_BRANCHES))}; "
            "repeatable)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    allowed = (
        frozenset(args.allow_branches)
        if args.allow_branches
        else DEFAULT_ALLOWED_BRANCHES
    )
    release_tag = args.tag or detect_github_release_tag()
    try:
        if release_tag is not None:
            return run_release_validation(
                tag=release_tag,
                root=args.repo_root,
                allow_dirty=args.allow_dirty,
                dist_dir=args.dist_dir,
            )
        return run_validation(
            root=args.repo_root,
            allow_dirty=args.allow_dirty,
            allowed_branches=allowed,
            dist_dir=args.dist_dir,
        )
    except ReleaseValidationError as exc:
        print(f"[FAIL] release validation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
