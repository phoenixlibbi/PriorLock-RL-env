# Packaging PriorLock (Harbor-style)

Goal: users never clone the monorepo. They install a CLI and start wrapping.

```bash
uv tool install priorlock          # after PyPI
priorlock info
priorlock wrap tasks/my-task
```

Same shape as Harbor: `uv tool install harbor` → `harbor run …`.

## What ships in the wheel

Only `src/priorlock/` (CLI, probes, cartridges, verifiers env).

Not in the wheel: `website/`, `jobs/`, `harbortasks/`,
`priorlock-env/` trial pack.

## Local build & smoke (no PyPI account needed)

```bash
# from repo root
uv build
# → dist/priorlock-0.1.1-py3-none-any.whl

# install the wheel into a clean tool env
uv tool install --force dist/priorlock-*.whl
priorlock --version
priorlock info
```

Or with pip:

```bash
python -m pip install build
python -m build
python -m venv /tmp/plx && /tmp/plx/bin/pip install dist/priorlock-*.whl
/tmp/plx/bin/priorlock info
```

## Publish to PyPI (one-time setup)

1. Create account at https://pypi.org (and enable 2FA).
2. Create an API token (Account → API tokens → "Entire account" or project-scoped).
3. Publish:

```bash
uv build
uv publish          # prompts for token, or set UV_PUBLISH_TOKEN
# or:  twine upload dist/*
```

4. Flip docs to the short form:

```bash
uv tool install priorlock
# pip install priorlock
```

Test first on TestPyPI if you want:

```bash
uv publish --publish-url https://test.pypi.org/legacy/
uv tool install --index-url https://test.pypi.org/simple/ priorlock
```

## Until PyPI is live

Users still get Harbor-style install from Git:

```bash
uv tool install "priorlock @ git+https://github.com/phoenixlibbi/PriorLock-RL-env.git"
```

That builds from `pyproject.toml`, installs only the package, and puts `priorlock`
on their PATH — no website/docs sitting in their project folder.

## Version bumps

Edit `version` in `pyproject.toml` and `src/priorlock/__init__.py` together,
tag `v0.1.2`, rebuild, publish.
