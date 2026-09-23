# Release

This document is the contributor guide for HA-DocGen releases.

It describes the process implemented by Modules 12.1–12.4. It does not
change that implementation.

The runtime application does not create tags, GitHub Releases or
distribution artifacts. Release automation lives in GitHub Actions
(ADR-062). Version discovery never uses Git (ADR-061).

---

# What this process does

A release:

1. Records the version in `tools/ha_docgen/version.py`.
2. Creates a Git tag in the form `vMAJOR.MINOR.PATCH` (optional SemVer
   prerelease or build metadata is allowed when `VERSION` uses the same
   string).
3. Runs the existing CI quality gates.
4. Rebuilds the wheel and source distribution.
5. Checks that the Git tag, `VERSION`, installed package metadata, wheel
   metadata and sdist metadata all match.
6. Uploads those files as GitHub Actions artifacts.
7. Creates a GitHub Release for the tag and attaches the same files.

A release does **not**:

- bump `VERSION` automatically
- generate or update `changelog.md`
- sign packages
- publish to PyPI
- rewrite Git history
- retag or delete tags

Those steps remain outside the current implementation. PyPI publishing,
changelog generation and automatic version bumps are later work.

---

# Prerequisites

## Quality gates

The Release workflow reuses `.github/workflows/ci.yml` via
`workflow_call`. The quality job is therefore identical to push and
pull-request CI:

| Gate | Command in CI |
|------|----------------|
| Ruff | `python -m ruff check tools/ha_docgen` |
| Tests and coverage | `python -m pytest --cov --cov-report=term --cov-report=xml` |
| Package build | `python -m build --sdist --wheel` |

The job fails on the first failed gate. Coverage is collected without a
numeric threshold; the full pytest suite is the gate.

Python is `3.14`. Pip caching uses `requirements.txt`,
`requirements-dev.txt` and `pyproject.toml`.

Run the same commands from the repository root before tagging so a
failed CI job is not the first signal.

## Version consistency

Before creating a tag:

- `tools.ha_docgen.version.VERSION` is the only authoritative version.
- The string must be valid SemVer 2.0 (`MAJOR.MINOR.PATCH`, optional
  prerelease and build metadata). Invalid values fail at import of
  `version.py`.
- Do not edit a second copy in `pyproject.toml`. That file reads
  `VERSION` at build time.
- The Git tag must encode the same version as `VERSION` (see
  [Versioning policy](#versioning-policy)).

The Release workflow repeats this check with
`.github/scripts/validate_release_version.py` after rebuilding
distributions. A mismatch fails the job before a GitHub Release exists.

## GitHub permissions

| Surface | Permission | Why |
|---------|------------|-----|
| `.github/workflows/ci.yml` | `contents: read` | Checkout and quality gates |
| `.github/workflows/release.yml` | `contents: write` | Create the GitHub Release and attach assets |
| Release job token | `secrets.GITHUB_TOKEN` | Passed to `gh release create` |

No extra repository secrets are configured for this workflow.

The person creating the release must be able to:

- push the commit that contains the `VERSION` change
- create and push an annotated or lightweight Git tag matching `v*.*.*`
- view GitHub Actions (to confirm the workflow and download artifacts)

`GITHUB_TOKEN` is provided by GitHub Actions. Contributors do not supply
it.

---

# Versioning policy

## Semantic Versioning

`VERSION` must match SemVer 2.0 as enforced by `parse_version()` in
`version.py`:

```text
MAJOR.MINOR.PATCH[-prerelease][+build]
```

Examples that are valid: `0.2.0`, `1.0.0-rc.1`, `1.0.0+gha`.

There is no automation that chooses MAJOR, MINOR or PATCH. Contributors
update `VERSION` by editing the source constant.

## Version source

| Surface | Source |
|---------|--------|
| Runtime / CLI / package `__version__` | `tools.ha_docgen.version.VERSION` via `get_version()` |
| Wheel and sdist metadata | `pyproject.toml` dynamic version from the same constant |
| GitHub Release title and notes | the Git tag name (`GITHUB_REF_NAME`) |

Git, Git tags, GitHub and environment repository state are never used to
discover the application version.

## Tag format

The Release workflow runs only on tag pushes matching `v*.*.*`.

The validator strips a leading `v` when the next character is a digit,
then requires an exact string match with `VERSION`.

| `VERSION` | Tag that matches | Tag that does not run or does not match |
|-----------|------------------|----------------------------------------|
| `0.2.0` | `v0.2.0` | `0.2.0` (does not match `v*.*.*`), `v0.2.1` (mismatch) |
| `1.0.0-rc.1` | `v1.0.0-rc.1` | `v1.0.0` (mismatch) |

Tag the exact value already recorded in `version.py`. The workflow never
rewrites `VERSION` to match a tag.

## Consistency requirements

All of the following must be the same string as `VERSION`:

1. Git tag after stripping a leading `v` (when the tag is `v` + digit…).
2. Installed distribution metadata (`importlib.metadata.version("ha-docgen")`).
3. Wheel `METADATA` `Version` field (exactly one `.whl` in `dist/`).
4. Sdist `PKG-INFO` `Version` field (exactly one `.tar.gz` in `dist/`).

Distribution `Name` must be `ha-docgen`. Extra wheels or sdists in
`dist/` fail validation.

---

# Creating a release

The workflow does not start from a branch name. It starts when a matching
tag is pushed. The development workflow in the HA-DocGen README still
applies: land the version change on `develop`, then `main`, then tag the
commit that contains that `VERSION`.

## 1. Update `VERSION`

Edit only:

```text
tools/ha_docgen/version.py
```

Set `VERSION` to the new SemVer string. Do not change runtime behaviour.

Confirm locally:

```bash
python -c "from tools.ha_docgen.version import VERSION; print(VERSION)"
python -m tools.ha_docgen.main --version
```

## 2. Commit and push the version change

Commit the `VERSION` update (and any other changes that belong in that
release) on a feature branch, merge to `develop`, then merge to `main`.

The Release workflow does not require a specific branch. Tagging a
commit that does not contain the intended `VERSION` will fail version
validation.

Push the branch or merged commit before tagging:

```bash
git push origin <branch>
```

Wait until CI on that commit is green. Tagging a red commit still
triggers the Release workflow, which then fails at the reused quality
job.

## 3. Create the Git tag

On the commit that contains the matching `VERSION`:

```bash
git tag v0.2.0
```

Replace `0.2.0` with the current `VERSION`. The tag name must start with
`v` and must match `v*.*.*` or the workflow will not run.

Do not move an existing tag onto a different commit unless you are
following [Recovery procedures](#recovery-procedures). GitHub will not
re-run the workflow for a tag that already exists on the remote until
that tag is deleted and pushed again.

## 4. Push the tag

```bash
git push origin v0.2.0
```

Pushing the tag is what starts `.github/workflows/release.yml`. Creating
a tag locally does nothing on GitHub.

## 5. GitHub Release workflow

On `push` of tags `v*.*.*`:

1. Job `quality` calls `.github/workflows/ci.yml` (Ruff, pytest with
   coverage, `python -m build`).
2. Job `release` runs only if `quality` succeeded.
3. It checks out the tagged commit, installs the project, and rebuilds
   `dist/` with `python -m build --sdist --wheel`.
4. It runs:

   ```bash
   python .github/scripts/validate_release_version.py \
     --tag "${GITHUB_REF_NAME}" \
     --dist-dir dist
   ```

5. It uploads `dist/*.whl` and `dist/*.tar.gz` as the workflow artifact
   `ha-docgen-distributions` (`if-no-files-found: error`).
6. It creates the GitHub Release:

   ```bash
   gh release create "${GITHUB_REF_NAME}" dist/*.whl dist/*.tar.gz \
     --title "HA-DocGen ${GITHUB_REF_NAME}" \
     --notes "HA-DocGen ${GITHUB_REF_NAME}"
   ```

Concurrency group is `release-${{ github.ref }}` with
`cancel-in-progress: false`. A second in-flight run for the same tag is
not cancelled.

Release notes are the tag name only. Changelog text is not generated.

## 6. Generated artifacts

After a successful run:

| Artifact | Location |
|----------|----------|
| Wheel | GitHub Actions artifact `ha-docgen-distributions` and GitHub Release assets |
| Source distribution | same |

Filenames come from the current `VERSION` (for example
`ha_docgen-0.2.0-py3-none-any.whl` and
`ha_docgen-0.2.0.tar.gz`). Exact names follow the setuptools build.

CI on ordinary pushes also builds distributions but does **not** upload
them or create a GitHub Release.

---

# Recovery procedures

Only recover with operations the current tooling already supports:
fix source, re-run GitHub Actions, or delete and recreate a Git tag.
There is no automated rollback, retag or PyPI yank.

## Failed CI (quality job)

The `release` job does not start. No GitHub Release is created.

1. Open the failed `quality` job and read which gate failed (Ruff,
   pytest, or build).
2. Fix the failure on a new commit. Do not retag the broken commit.
3. Push the fix and wait for CI on that commit.
4. If a tag already exists on the broken commit, delete it locally and
   on the remote, then create the same tag name on the fixed commit:

   ```bash
   git tag -d v0.2.0
   git push origin :refs/tags/v0.2.0
   git tag v0.2.0
   git push origin v0.2.0
   ```

If the failure was a transient GitHub Actions fault and the commit is
already correct, use **Re-run jobs** on that workflow run. Do not invent
a second tag name for the same version.

## Failed Release workflow (after quality)

Quality passed; a later step failed (install, build, version validation,
artifact upload, or `gh release create`). No GitHub Release exists unless
`gh release create` itself succeeded.

1. Read the failed step log.
2. Version mismatch: follow [Incorrect tag or version mismatch](#incorrect-tag-or-version-mismatch).
3. Missing or extra artifacts: follow [Failed artifact generation](#failed-artifact-generation).
4. `gh release create` failed because a Release for that tag already
   exists: do not run the create command again. Inspect the existing
   Release. If it is wrong, delete that GitHub Release in the GitHub UI
   (or `gh release delete <tag>`), then re-run the workflow or retag as
   appropriate.
5. Transient infrastructure failure: **Re-run jobs** on the same tag
   commit after confirming no Release exists yet.

Re-running a run that already created the Release will fail at
`gh release create` because the tag already has a Release.

## Incorrect tag

Symptoms: the workflow never starts (`v*.*.*` did not match), or it
starts and version validation fails.

The workflow does not move or rewrite tags.

1. Leave `VERSION` as the intended release version, or edit it if the
   tag was correct and the source was wrong.
2. Delete the incorrect tag locally and on the remote (commands above).
3. Create the tag that matches `VERSION` on the correct commit.
4. Push the tag.

Do not force-push `main` or `develop` to “fix” a tag.

## Version mismatch

`validate_release_version.py` fails when the tag, installed package,
wheel or sdist disagrees with `VERSION`.

1. Do not create a GitHub Release by hand to bypass the check.
2. Identify which value differs (tag vs `VERSION` vs metadata).
3. If `VERSION` is wrong: change `version.py`, commit, retag the new
   commit.
4. If the tag is wrong: delete and recreate it so it matches `VERSION`.
5. If metadata is wrong: the build did not read `VERSION`. That is a
   packaging defect; fix source and rebuild. Do not edit files inside
   `dist/` and re-upload them.

## Failed artifact generation

Build produced no files, more than one wheel or sdist, or
`upload-artifact` reported `if-no-files-found: error`.

1. Inspect the **Build distributions** log. `python -m build` must write
   exactly one `.whl` and one `.tar.gz` into `dist/`.
2. Fix the packaging problem in source (not in a hand-edited `dist/`).
3. Retag or re-run as for a failed CI job.

There is no supported path that publishes a locally built `dist/` as the
official GitHub Release without the workflow’s validation step.

---

# Troubleshooting

## Version mismatch

The validator prints which label failed (`Git tag`, `package metadata`,
`wheel metadata`, or `sdist metadata`). Compare that string to
`tools.ha_docgen.version.VERSION`.

Local reproduction after a build:

```bash
python -m build --sdist --wheel
python .github/scripts/validate_release_version.py --tag v0.2.0 --dist-dir dist
```

Use the tag you intend to push. The script is release infrastructure; it
is not part of the HA-DocGen runtime package.

## Missing artifacts

- CI on push/PR builds `dist/` but does not upload it. Missing files on
  a non-tag run are expected.
- The Release upload step requires both a wheel and an sdist. An empty
  `dist/` fails the job.
- Validation requires exactly one file per suffix. Leftover files in
  `dist/` on the runner are unlikely; locally, clean `dist/` before
  reproducing.

## Workflow did not start

- The ref is not a tag, or the tag does not match `v*.*.*`.
- The tag was created locally but not pushed.
- Actions are disabled for the repository.

## Workflow failed at quality

Treat it as ordinary CI. The Release job will not run until quality
passes. See [Failed CI](#failed-ci-quality-job).

## Workflow failed at `gh release create`

- A Release for that tag already exists.
- `contents: write` is missing (the workflow file currently sets it;
  do not remove it).
- `GITHUB_TOKEN` cannot create Releases (org policy). That is a GitHub
  administration issue, not an application defect.

## Tag already exists

`git push origin v0.2.0` is rejected. Either use the existing tag (and
the existing Release, if any) or delete the remote tag and recreate it
on the intended commit. Moving tags is a recovery action, not the normal
release path.

## CLI version differs from the tag

The tagged commit’s `VERSION` is what the Release must match. A local
checkout on another commit can print a different version. Compare
`python -m tools.ha_docgen.main --version` on the tagged commit.

---

# Release checklist

Use this list for every release.

- [ ] `VERSION` in `tools/ha_docgen/version.py` is the intended SemVer string
- [ ] No second version copy was edited in `pyproject.toml`
- [ ] `python -m ruff check tools/ha_docgen` passes
- [ ] `python -m pytest --cov --cov-report=term --cov-report=xml` passes
- [ ] `python -m build --sdist --wheel` produces one wheel and one sdist
- [ ] Local `python -m tools.ha_docgen.main --version` prints `VERSION`
- [ ] Version change is committed and pushed (`develop` then `main` as usual)
- [ ] Push/PR CI on that commit is green
- [ ] Git tag is `v` + `VERSION` (example: `v0.2.0`)
- [ ] Tag is pushed to `origin`
- [ ] Release workflow `quality` job is green
- [ ] Release workflow version validation is green
- [ ] Artifact `ha-docgen-distributions` contains the wheel and sdist
- [ ] GitHub Release exists for the tag with title `HA-DocGen <tag>`
- [ ] GitHub Release assets are the same wheel and sdist

PyPI upload, changelog generation and signing are not part of this
checklist.
