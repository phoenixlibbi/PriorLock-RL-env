# Study 2 plan: silent dependency changes inside real repositories (SWE-bench Pro public set)

Status: **planned, not started.** Study 1 (bench v2, synthetic libraries in generated repositories) is running; see the main [README](../README.md). This document is the handover for whoever builds Study 2.

## 1. Why a second study

Study 1 shows the effect under control: models apply a documented behaviour change when they are handed the docs (93–100% right calls) but mostly do not find the docs themselves (8–33%). It cannot show that this happens in real software, because its libraries and repositories are generated. Study 2 keeps the question and the verifier, and replaces the generated parts with real ones:

| | Study 1 (now) | Study 2 (this plan) |
|---|---|---|
| Repository | generated mini-project | a complete real repository at a real commit |
| Environment | `python:3.11` + task files | the repository's own Docker image (dependencies pinned and installed) |
| Library | synthetic (`funckit`, …) | a real dependency the project uses (PyYAML, Jinja2, python-dateutil, …) |
| Behaviour change | synthetic | **counterfactual**: one real function's behaviour silently changed in the installed copy and documented in that library's own style |
| Task | "data-processing checks" naming the function | a short, natural change to the real project that needs that function |
| Grading | the library call + output | the library call (same verifier) + the repository's own tests |

## 2. Design decision: counterfactual changes, not "releases after the cutoff"

Training cutoffs are unknown, differ between models and keep moving, so an experiment built on "releases the model has not seen" cannot be reproduced. Instead, each task changes a real function in a way that **never existed**: no model can have trained on it, the same patched environment gives the same test for every model in any year, and there is no limit on how many changes can be made. The model's pull toward the old behaviour is real, because it knows the real library well.

A **closed-book check per model** is still required (not for cutoffs): run the task with no repository access and confirm the model uses the *original* behaviour. A change the model happens to guess right is dropped for that model.

## 3. Why SWE-bench Pro's public set fits

[SWE-bench Pro](https://arxiv.org/abs/2509.16941) tasks are very hard (under 25% solved), but Study 2 does **not** use its tasks, only its repositories and environments:

- complete, actively maintained codebases with real docs, tests and CI;
- a ready, pinned Docker image per instance (`ghcr.io/scaleapi/swe-bench_pro-v2:<tag>`), which removes the most expensive step of building environments;
- many base commits per repository, so tasks can be spread across versions;
- our own tasks stay small and isolated, so a failure means "did not notice the change", not "could not solve a huge PR".

## 4. Survey of the public set (2026-10-29)

Source: Hugging Face `ScaleAI/SWE-bench_Pro` (config `default`, 642 tasks), the GitHub API and the registry manifests (metadata only; nothing was downloaded). Raw data: [`swebench-pro-survey.json`](swebench-pro-survey.json).

| Repository | Tasks | Language | Licence | Stars | Repo size | Image (compressed) |
|---|---|---|---|---|---|---|
| ansible/ansible | 82 | Python | GPL-3.0 | 71k | 261 MB | 0.75 GB |
| internetarchive/openlibrary | 82 | Python | AGPL-3.0 | 6.8k | 126 MB | 1.07 GB |
| qutebrowser/qutebrowser | 73 | Python | GPL-3.0 | 11.7k | 64 MB | 0.75 GB |
| flipt-io/flipt | 78 | Go | not asserted | 4.9k | 107 MB | 1.93 GB |
| gravitational/teleport | 68 | Go | AGPL-3.0 | 21k | 1.5 GB | 3.50 GB |
| future-architect/vuls | 58 | Go | GPL-3.0 | 12.3k | 32 MB | 1.20 GB |
| navidrome/navidrome | 52 | Go | GPL-3.0 | 24.4k | 71 MB | 0.92 GB |
| protonmail/webclients | 55 | JavaScript | GPL-3.0 | 5.7k | 4.2 GB | 6.52 GB |
| element-hq/element-web | 52 | JavaScript | AGPL-3.0 | 13.6k | 613 MB | 1.84 GB |
| NodeBB/NodeBB | 38 | JavaScript | GPL-3.0 | 15.2k | 111 MB | 0.98 GB |
| tutao/tutanota | 4 | TypeScript | GPL-3.0 | 8.1k | 288 MB | 1.21 GB |

**Python repositories and the dependencies they pin** (candidates for counterfactual changes):

| Repository | Third-party dependencies (from `requirements*.txt` at a base commit) |
|---|---|
| ansible/ansible | PyYAML, cryptography, jinja2, packaging, resolvelib |
| internetarchive/openlibrary | Babel, beautifulsoup4, python-dateutil, httpx, lxml, Pillow, pydantic, PyYAML, feedparser, isbnlib, pymarc, … |
| qutebrowser/qutebrowser | Jinja2, MarkupSafe, PyYAML, Pygments, attrs, colorama, cssutils |

**Recommended pilot repositories:** `internetarchive/openlibrary` (the widest spread of everyday dependencies: dates, HTML, HTTP, YAML) and `ansible/ansible` (PyYAML and Jinja2 at the centre of the project, the largest community). Both have small images and many base commits. `qutebrowser` is a good third (needs Qt, so its tests may be heavier).

## 5. How a task is built

1. **Pick a repository and base commit**, and pull that instance's Docker image.
2. **Pick a dependency function the project really calls** (search the codebase), with a parameter or behaviour a model has a strong prior about. Examples to evaluate: `yaml.dump(sort_keys=…)`, `dateutil.parser.parse(dayfirst=…)`, `jinja2.Environment(autoescape=…)`, `BeautifulSoup.get_text(strip=…)`, `packaging.specifiers.SpecifierSet(prereleases=…)`.
3. **Make the counterfactual change in the installed copy** inside the image (`site-packages`): same signature, plausible new behaviour (flip a default, change what one option value means, or change an edge case). Bump the installed version (for example PyYAML 6.0.1 → 7.0.0) consistently in `__version__` and the `dist-info` metadata.
4. **Document it where that ecosystem documents changes**, in exactly one channel per task: the function's docstring in the installed source, the package's changelog / release notes in `dist-info`, the project's own changelog or upgrade notes ("bumped PyYAML to 7.0"), or a comment next to the pin in `requirements.txt`. Keep a channel-isolation check, as in Study 1.
5. **Write a short, natural task in the project** that needs that function (a small feature, helper or fix, a few lines to a few dozen), with the instruction in the project's issue style and no hint that anything changed.
6. **Grade two ways:** the call-observing verifier wraps the real dependency function and records the arguments the agent's code passed (documented call 1.0 / memorized call 0.40 / not called 0), and the repository's own tests check nothing else broke. Write hidden tests that distinguish the old and new behaviour.
7. **Validate before any model runs:** a gold patch scores 1.0, a memorized-behaviour patch scores 0.40, a no-op scores 0, the repository's tests pass on gold, and the closed-book check shows the prior.

## 6. Things to check first

- **Licences.** The public set is copyleft (GPL-3.0 / AGPL-3.0; flipt does not assert one). Use the repositories for research, but **do not redistribute the repositories or images**: publish each task as a patch plus a setup script that pulls the original image. Any file we publish that is derived from a repository's code goes in a separate folder under that repository's licence. The counterfactual patches touch the *dependencies* (PyYAML MIT, Jinja2 BSD-3, python-dateutil Apache-2.0/BSD), which keeps those simple.
- **Language.** The call-observing verifier is Python-only today. Start with the three Python repositories; Go and JavaScript need a language-specific way to observe calls.
- **Disk and architecture.** Images are 0.75–6.5 GB compressed and x86-only. The three Python images total about 2.6 GB.
- **Effort.** About 1–2 hours per task done properly. Pilot: 2 repositories × 5 tasks. Paper: 20–30 tasks.
- **Agent.** Real repositories are large. The minimal agent may need more turns, or a standard scaffold (Terminus-2 through Harbor, mini-swe-agent) with shell access; log every command so "did it read the docs" can still be answered.
- **Where Python docs really live.** Installed Python packages ship readable source and docstrings, not release notes. So the realistic channels differ from Study 1: the installed source and docstring, `dist-info` metadata, the project's own changelog or pin comment. Decide the channel set before building tasks.
- **Budget.** A real-repository episode uses several times more calls than a Study 1 episode. Pilot on free tiers with one or two models; frontier models need credits.

## 7. Conditions and metrics

Reuse Study 1's conditions where they apply: closed-book (the prior), docs in the prompt (ceiling), agent with repository access and no hint, the "check the documentation" hint, and code execution (natural here, since the image can run the project). Report right calls, prior-locked calls, whether the agent opened the channel, and the repository's test pass rate, with intervals that resample behaviour changes.

## 8. Pilot checklist

- [ ] Pull the images for one openlibrary and one ansible base commit; confirm the repository tests run.
- [ ] For each, list five dependency functions the project calls; run the closed-book prior check on two free models; keep the five strongest priors.
- [ ] Build one task end to end (patch, docs channel, task text, hidden test, call grader); validate the reference ladder.
- [ ] Build the remaining nine; run the free models; compare with Study 1.
