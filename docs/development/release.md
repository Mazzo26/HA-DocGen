# Release

This document is the contributor guide for HA-DocGen releases.

It describes the process implemented by Modules 12.1–12.4. It does not
change that implementation.

The runtime application does not create tags, GitHub Releases or
distribution artifacts. Release automation lives in GitHub Actions
(ADR-062). Version discovery never uses Git (ADR-061).

---

# Release validation

Before creating a release tag, confirm the repository is ready. Release
validation is infrastructure only: it does not create tags, GitHub
Releases, or publish packages.

The single entry point is `.github/scripts/release_validation.py`. It
checks the working tree, branch, required files, authoritative version
resolution (including the dynamic `pyproject.toml` attribute),
`python -m build`, `twine check`, distribution metadata consistency, and
that the intended `vVERSION` tag is absent locally and on `origin`.

## Local

From the repository root, with an editable install (`pip install -e ".[dev]"`):

```bash
python .github/scripts/release_validation.py
```

The working tree must be clean. For local iteration only:

```bash
python .github/scripts/release_validation.py --allow-dirty
```

A non-zero exit status means at least one check failed; each failure is
printed with a reason.

## GitHub Actions

Use the **Release Validation** workflow (`.github/workflows/release-validation.yml`):

1. Open **Actions** → **Release Validation**.
2. Choose **Run workflow** on the branch to validate.
3. Confirm the job is green before tagging.

The workflow checks out the repository (including tags), installs
`pip install -e ".[dev]"`, and runs the same validation script. It does
not publish artifacts or create a GitHub Release.

---

# What this process does

A release:

1. Records the version in `src/ha_docgen/version.py`.
2. Creates a Git tag in the form `vMAJOR.MINOR.PATCH` (optional SemVer
   prerelease or build metadata is allowed when `VERSION` uses the same
   string).
3. Runs release validation (`.github/scripts/release_validation.py`).
4. Rebuilds the wheel and source distribution.
5. Checks distributions with `twine check`.
6. Creates a GitHub Release for the tag and attaches the wheel and sdist.

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

Push and pull-request CI (`.github/workflows/ci.yml`, workflow name **CI**)
runs on Python 3.14:

| Gate | Command in CI |
|------|----------------|
| Dependency check | `python -m pip check` |
| Tests | `python -m pytest` |
| Package build | `python -m build` |
| Distribution check | `twine check dist/*` |

The job fails on the first failed gate. CI also uploads `dist/` as a
workflow artifact. The full pytest suite is the test gate; no coverage
threshold is configured.

Before tagging, run release validation locally or via the **Release
Validation** workflow so a failed Release job is not the first signal.

## Version consistency

Before creating a tag:

- `ha_docgen.version.VERSION` is the only authoritative version.
- The string must be valid SemVer 2.0 (`MAJOR.MINOR.PATCH`, optional
  prerelease and build metadata). Invalid values fail at import of
  `version.py`.
- Do not edit a second copy in `pyproject.toml`. That file reads
  `VERSION` at build time.
- The Git tag must encode the same version as `VERSION` (see
  [Versioning policy](#versioning-policy)).

The Release workflow runs
`.github/scripts/release_validation.py` before creating a GitHub Release.
A mismatch fails the job before a Release exists.

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

Examples that are valid: `1.0.0`, `1.0.0-rc.1`, `1.0.0+gha`.

There is no automation that chooses MAJOR, MINOR or PATCH. Contributors
update `VERSION` by editing the source constant.

## Version source

| Surface | Source |
|---------|--------|
| Runtime / CLI / package `__version__` | `ha_docgen.version.VERSION` via `get_version()` |
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
| `1.0.0` | `v1.0.0` | `1.0.0` (does not match `v*.*.*`), `v1.0.1` (mismatch) |
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
src/ha_docgen/version.py
```

Set `VERSION` to the new SemVer string. Do not change runtime behaviour.

Confirm locally:

```bash
python -c "from ha_docgen.version import VERSION; print(VERSION)"
python -m ha_docgen --version
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
triggers the Release workflow, which then fails at release validation.

## 3. Create the Git tag

On the commit that contains the matching `VERSION`:

```bash
git tag v1.0.0
```

Replace `1.0.0` with the current `VERSION`. The tag name must start with
`v` and must match `v*.*.*` or the workflow will not run.

Do not move an existing tag onto a different commit unless you are
following [Recovery procedures](#recovery-procedures). GitHub will not
re-run the workflow for a tag that already exists on the remote until
that tag is deleted and pushed again.

## 4. Push the tag

```bash
git push origin v1.0.0
```

Pushing the tag is what starts `.github/workflows/release.yml`. Creating
a tag locally does nothing on GitHub.

## 5. GitHub Release workflow

On `push` of tags `v*.*.*` (workflow name **Release**,
`.github/workflows/release.yml`):

1. Checks out the tagged commit (`fetch-depth: 0`).
2. Sets up Python 3.14 and installs with `pip install -e ".[dev]"`.
3. Runs `python .github/scripts/release_validation.py`.
4. Rebuilds distributions with `python -m build`.
5. Runs `twine check dist/*`.
6. Creates the GitHub Release:

   ```bash
   gh release create "${GITHUB_REF_NAME}" dist/*.whl dist/*.tar.gz \
     --title "HA-DocGen ${GITHUB_REF_NAME}" \
     --generate-notes
   ```

Release notes are generated by GitHub (`--generate-notes`). Changelog text
is not synthesised by the workflow.

## 6. Generated artifacts

After a successful run:

| Artifact | Location |
|----------|----------|
| Wheel | GitHub Release assets |
| Source distribution | GitHub Release assets |

Filenames come from the current `VERSION` (for example
`ha_docgen-1.0.0-py3-none-any.whl` and
`ha_docgen-1.0.0.tar.gz`). Exact names follow the setuptools build.

CI on ordinary pushes also builds distributions and uploads them as a
workflow artifact, but does **not** create a GitHub Release.

---

# Recovery procedures

Only recover with operations the current tooling already supports:
fix source, re-run GitHub Actions, or delete and recreate a Git tag.
There is no automated rollback, retag or PyPI yank.

## Failed CI

If push/PR CI is red, do not tag that commit.

1. Open the failed **CI** job and read which gate failed (`pip check`,
   pytest, build, or twine).
2. Fix the failure on a new commit. Do not retag the broken commit.
3. Push the fix and wait for CI on that commit.
4. If a tag already exists on the broken commit, delete it locally and
   on the remote, then create the same tag name on the fixed commit:

   ```bash
   git tag -d v1.0.0
   git push origin :refs/tags/v1.0.0
   git tag v1.0.0
   git push origin v1.0.0
   ```

If the failure was a transient GitHub Actions fault and the commit is
already correct, use **Re-run jobs** on that workflow run. Do not invent
a second tag name for the same version.

## Failed Release workflow

A later step failed (install, release validation, build, twine, or
`gh release create`). No GitHub Release exists unless
`gh release create` itself succeeded.

1. Read the failed step log.
2. Version mismatch: follow [Version mismatch](#version-mismatch).
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

`release_validation.py` fails when the tag, installed package,
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
`ha_docgen.version.VERSION`.

Local reproduction after a build:

```bash
python -m build --sdist --wheel
python .github/scripts/release_validation.py --tag v1.0.0 --dist-dir dist
```

Use the tag you intend to push. The script is release infrastructure; it
is not part of the HA-DocGen runtime package.

## Missing artifacts

- CI on push/PR builds and uploads `dist/` as a workflow artifact, but
  does not create a GitHub Release.
- The Release create step requires both a wheel and an sdist. An empty
  `dist/` fails the job.
- Validation requires exactly one file per suffix. Leftover files in
  `dist/` on the runner are unlikely; locally, clean `dist/` before
  reproducing.

## Workflow did not start

- The ref is not a tag, or the tag does not match `v*.*.*`.
- The tag was created locally but not pushed.
- Actions are disabled for the repository.

## Workflow failed at validation or build

Treat it as a release-validation or packaging failure. Fix source, then
retag or re-run. See [Failed CI](#failed-ci).

## Workflow failed at `gh release create`

- A Release for that tag already exists.
- `contents: write` is missing (the workflow file currently sets it;
  do not remove it).
- `GITHUB_TOKEN` cannot create Releases (org policy). That is a GitHub
  administration issue, not an application defect.

## Tag already exists

`git push origin v1.0.0` is rejected. Either use the existing tag (and
the existing Release, if any) or delete the remote tag and recreate it
on the intended commit. Moving tags is a recovery action, not the normal
release path.

## CLI version differs from the tag

The tagged commit’s `VERSION` is what the Release must match. A local
checkout on another commit can print a different version. Compare
`python -m ha_docgen --version` on the tagged commit.

---

# Release checklist

Use this list for every release.

## Preparation (Phase 6.2)

- [x] `VERSION` in `src/ha_docgen/version.py` is the intended SemVer string (`1.0.0`)
- [x] No second version copy was edited in `pyproject.toml` (dynamic attribute retained)
- [x] Packaging classifiers and issue-template placeholders match Version 1.0.0
- [x] User-facing `CHANGELOG.md` completed for Version 1.0.0
- [x] Documentation reviewed for version and release consistency
- [x] `python -m pytest` passes
- [x] Ruff / lint quality gates pass (via local run or CI)
- [x] `python -m build` produces one wheel and one sdist
- [x] `twine check dist/*` passes
- [x] Installation verified from the wheel in an isolated environment
- [x] Installation verified from the sdist in an isolated environment
- [x] After install: `ha-docgen --help` and `ha-docgen --version` succeed
- [x] Local `python -m ha_docgen --version` prints `HA-DocGen 1.0.0`
- [x] Package metadata reports version `1.0.0`
- [x] Distributions contain no development artifacts (`tests/`, caches, etc.)
- [x] Ready for GitHub Release (Phase 6.3)

## Publishing (Phase 6.3)

- [ ] Version change is committed and pushed (`develop` then `main` as usual)
- [ ] Push/PR CI on that commit is green
- [ ] `python .github/scripts/release_validation.py` passes (or Release Validation workflow is green)
- [ ] Git tag is `v` + `VERSION` (example: `v1.0.0`)
- [ ] Tag is pushed to `origin`
- [ ] Release workflow validation, build and twine steps are green
- [ ] GitHub Release exists for the tag with title `HA-DocGen <tag>`
- [ ] GitHub Release assets are the same wheel and sdist

PyPI upload and package signing are not part of this checklist.
