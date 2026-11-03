# Community "Open the Forge" starter-issue drafts v0

**Cut:** CUT-A2A-COMMUNITY-P0-20261103 ("Open the Forge")
**Status:** DRAFTS ONLY — DO NOT PUBLISH. These are proposed GitHub issue texts for
Director review; nothing has been posted on GitHub, and creating the issues is a
separate, Director-authorized step.

Drafts are non-duplicative (README/acceptance-gates documentation, observatory test
coverage, repository hygiene), small, and each was verified against the worktree at
base `cc7eec4ee0f84f9d501fe0d891d2f8f8f363b9a9`. None touches authentication,
credentials, wallets, trust-boundary enforcement logic, or production hosting.

---

## Draft 1 — Document the AO-P0A observatory cut in README and the acceptance-gates ledger

**Title:** `Document the AO-P0A observatory data-foundation cut (README + acceptance gates)`

**Labels:** `documentation`, `good first issue`

**Objective:** the newest cut (AO-P0A, commit `cc7eec4` "feat(a2a): AO-P0A agent
observatory data foundation") is missing from both status ledgers that every other cut
has: `README.md` has per-cut sections ending at P0-WEB-03B2A and says nothing about the
observatory, and `docs/agent-web/acceptance-gates-v0.md` has no AO-P0A section. A
reader cannot see from the project's own ledgers that the observatory exists, that it
is a PRIVATE owner-dashboard foundation, or that nothing is deployed.

**Relevant file paths:**

- `README.md` (add an "## AO-P0A — agent observatory data foundation (local-only)" section after the P0-WEB-03B2A section; pure addition)
- `docs/agent-web/acceptance-gates-v0.md` (add an "## AO-P0A" section after the P0-WEB-03B2A section)
- `docs/agent-web/observatory-data-foundation-v0.md` (read-only reference for accurate wording; do not rewrite it)

**Expected deliverable:** two short, purely additive sections (one per ledger) that
state what AO-P0A built (`observatory/model.py`, `observatory/feed.py`,
`observatory/contract.py`, `contracts/agent-web/observatory-feed.v0.schema.json`),
its local-synthetic read-only status, and the standard "NOT DEPLOYED" caution —
matching the voice of the existing per-cut README sections.

**Acceptance criteria:**

- [ ] `README.md` gains a dated AO-P0A section near the end, after P0-WEB-03B2A, with a link to `docs/agent-web/observatory-data-foundation-v0.md`.
- [ ] A "NOT DEPLOYED."-style caution sentence is present, consistent in strength with the other per-cut cautions (no weakened or removed wording anywhere).
- [ ] `docs/agent-web/acceptance-gates-v0.md` gains an AO-P0A section with at least the gates already recorded in the observatory cut doc.
- [ ] No existing README or gates text is modified, reworded, or deleted (addition only).

**Local verification:**

```sh
git clone https://github.com/ToadAid/toadaid-a2a.git
cd toadaid-a2a
git diff --check
grep -c 'AO-P0A' README.md docs/agent-web/acceptance-gates-v0.md   # >= 1 each
python3 -m unittest discover -s tests -v                          # all OK
```

**Scope restrictions — do NOT touch:** `observatory/`, `agent_web/`, `contracts/`,
`tests/`, `.github/`, any existing warning/status sentence, or the architecture master
note. Documentation only.

---

## Draft 2 — Add fail-closed regression tests for five untested observatory refusal codes

**Title:** `Tests: cover the five untested fail-closed Observatory refusal codes`

**Labels:** `tests`, `good first issue`

**Objective:** `observatory/feed.py` enforces several fail-closed refusal paths that
currently have **no test coverage** anywhere in `tests/`. Specifically, these codes are
raised in `observatory/feed.py` but appear in no test file (verified by searching
`tests/` for each code): `FEED_CAPACITY_OUT_OF_BOUNDS` (constructor capacity bounds,
`feed.py` line 183), `PAGINATION_KEYS_NOT_ADMITTED` (line 309),
`FILTER_AGENT_REF_NOT_ADMITTED` (line 304), `PAGE_OFFSET_PAST_END` (line 320), and
`PRODUCER_BINDINGS_SHAPE_INVALID` (`synthetic_offline_authenticator` called with a
non-dict or empty bindings mapping, lines 112/116). Fail-closed seams are the
repository's core safety pattern, so each refusal deserves a named regression test, not
an incidental assertion.

**Relevant file paths:**

- `tests/test_observatory_foundation.py` (add tests; read-only reference for the existing patterns)
- `observatory/feed.py` (read-only reference for the exact refusal codes and raise conditions)

**Expected deliverable:** one new test method per refusal code, following the existing
test style in `tests/test_observatory_foundation.py` (e.g. construct a `FeedRecorder`
with `capacity=0` and `capacity=MAX_EVENTS + 1` and assert `ObservatoryRefusal` with
code `FEED_CAPACITY_OUT_OF_BOUNDS`; request `filters={"agentRef": "bad"}` and assert
`FILTER_AGENT_REF_NOT_ADMITTED`; pass `pagination={"unexpected": 1}` and assert
`PAGINATION_KEYS_NOT_ADMITTED`; request `pageToken="cur:999999999"` past the end and
assert `PAGE_OFFSET_PAST_END`; call `synthetic_offline_authenticator({})` /
`synthetic_offline_authenticator("x")` and assert `PRODUCER_BINDINGS_SHAPE_INVALID`).

**Acceptance criteria:**

- [ ] Each of the five refusal codes listed above is asserted in at least one test that triggers it deliberately.
- [ ] Tests live in `tests/test_observatory_foundation.py`, use `unittest` and stdlib only, and follow existing naming/style.
- [ ] No source file under `observatory/` is changed (tests only in this cut).
- [ ] Full suite passes: `python3 -m unittest discover -s tests -v` (baseline is 236 tests; this adds at least 5).

**Local verification:**

```sh
git clone https://github.com/ToadAid/toadaid-a2a.git
cd toadaid-a2a
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v   # OK, count increased
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_observatory_foundation -v
git diff --check
```

**Scope restrictions — do NOT touch:** `observatory/**` (no behavior change, including
no new refusal codes; the point is coverage of existing ones), authentication or
authorization logic, `agent_web/`, `contracts/`, and `.github/`.

---

## Draft 3 — Add a `.gitignore` so running the documented test command leaves the worktree clean

**Title:** `DX: add .gitignore for __pycache__ so the documented test command does not dirty the worktree`

**Labels:** `good first issue`, `help wanted`

**Objective:** `README.md` (five times) and `CONTRIBUTING.md` tell contributors to run
`python3 -m unittest discover -s tests -v`. Running that command on a clean checkout
creates `__pycache__/` directories under `agent_web/`, `observatory/`, `tests/` and
`tools/`, and — because the repository has **no `.gitignore`** — `git status --porcelain`
immediately shows four untracked paths that have nothing to do with anyone's change.
New contributors will either commit those directories or think their checkout is
broken. Verified on the base commit: a test run does create exactly
`agent_web/__pycache__/`, `observatory/__pycache__/`, `tests/__pycache__/`,
`tools/__pycache__/` as untracked.

**Relevant file paths:**

- `.gitignore` (new file at repository root)

**Expected deliverable:** a small `.gitignore` containing, at minimum:

```gitignore
__pycache__/
*.pyc
```

Nothing more. Do not ignore `.json`, `.md`, logs, or anything else that might silently
hide real changes on a future cut.

**Acceptance criteria:**

- [ ] A root `.gitignore` exists with the two patterns above (or narrower equivalents covering exactly `__pycache__` and compiled bytecode).
- [ ] After `python3 -m unittest discover -s tests -v` on a fresh clone, `git status --porcelain` is empty.
- [ ] `git check-ignore -v agent_web/__pycache__` reports the new rule.
- [ ] Existing tracked files are unaffected: `git ls-files | git diff --check` clean and the full suite still passes.

**Local verification:**

```sh
git clone https://github.com/ToadAid/toadaid-a2a.git
cd toadaid-a2a
python3 -m unittest discover -s tests -v        # leaves untracked __pycache__ dirs before fix
git status --porcelain                          # shows 4 paths before fix
git ls-files | xargs wc -l >/dev/null || true   # tracked inventory unchanged
git diff --check                                # clean
```

**Scope restrictions — do NOT touch:** any other directory (`agent_web/`,
`observatory/`, `tests/`, `tools/`, `contracts/`, `.github/`), and do not broaden the
ignore list (over-broad ignores can hide future contract or evidence files in this
ledger-driven repository). If a second DX improvement is wanted in the same PR, stop —
keep it one cut.