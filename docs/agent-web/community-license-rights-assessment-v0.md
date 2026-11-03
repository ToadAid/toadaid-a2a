# Community cut license rights assessment v0

**Cut:** CUT-A2A-COMMUNITY-P0-20261103 ("Open the Forge")
**Status:** ASSESSMENT SUPERSEDED BY THE DIRECTOR RULING (see section 8) —
the assessment is retained verbatim below as the evidence record behind the
approval decision.

**Author of this cut:** ToadAid (Director-authorized local worktree cut; committed in
`/home/tommy/toadaid-worktrees/toadaid-a2a-community-p0`, branch
`cut-a2a-community-p0-open-the-forge-20261103`, base `cc7eec4ee0f84f9d501fe0d891d2f8f8f363b9a9`)
**Scope:** community onboarding artifacts only (`LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`,
`README.md` addition, two docs). This is NOT an A2A runtime, protocol, admission or
security change, and it does not assert that anything in this repository is deployed
or certified.

---

## 8. Director licensing decision — APPROVED (2026-11-03)

The ToadAid Director approved the MIT License for `ToadAid/toadaid-a2a`:

- **License:** MIT (standard text as `LICENSE` at the repository root).
- **Copyright holder:** `Copyright (c) 2026 ToadAid`.
- **Scope:** original A2A repository code and documentation for which
  ToadAid possesses the necessary licensing rights (per sections 3–5).
- **Third-party materials retain their own rights**; nothing here licenses
  upstream projects' code, text, or marks beyond factual metadata references.
- **Original Tobyworld lore is not relicensed** — its rights remain UNKNOWN
  (P0-WEB-03A/03B1/03B2A unchanged).

Resolved director questions from section 7: Q1 — copyright holder is
"ToadAid" (confirmed 2026-11-03); Q5 — the approval (this section)
precedes any public announcement of the repository being MIT. Q2–Q4
(public contact address; future vendoring policy; TCK-artifact
licensing) remain open for future rulings and are NOT resolved by this
approval.

---

## 1. Question (original assessment — evidence record)

**Original question.** May ToadAid apply the MIT License to `ToadAid/toadaid-a2a`,
and if so, what third-party notice obligations exist?

## 2. Method used

Evidence-gathering only; no upstream downloads, no network calls, no GitHub writes.

1. Read `README.md` in full to establish what the repository is (architecture-first,
   local-only, not-deployed status ledger) and what its per-cut entries claim.
2. Enumerated every commit on `HEAD` (`cc7eec4..3384465`, 16 commits) and recorded
   author name/email and committer name/email for each via
   `git log --format='%h %an <%ae> | cn=%cn <%ce>'`.
3. Searched all tracked content for references to third-party licenses, upstreams and
   copied material: `git grep -niE 'apache|mit licen|copyright|licensed under|a2aproject|tck'`.
4. Checked repository contents for vendored upstream material: full file inventory
   (`git ls-files`, 58 files, 9,242 total lines), largest blob check
   (`git rev-list --objects --all | git cat-file --batch-check` — largest blob is the
   observatory test file at ~50 KB; no `.proto`, no vendored package, no third-party
   license text, no binary artifacts), and a scan for strings that would indicate copied
   upstream spec text.
5. Read the two upstream-reference contract files (`contracts/agent-web/a2a-upstream-v1.0.1.json`
   and `contracts/agent-web/a2a-tck-pin-20261030.json`) in full to confirm they contain
   metadata only.
6. Ran the full offline test suite to confirm the repository is self-contained
   (236 tests, `OK`).

## 3. Evidence found

### 3.1 Commit authorship — uniform, single account

All 16 commits in history list **author** `ToadAid <ToadaidDAO@gmail.com>`. No other
author appears. Committers are:

| Committer                              | Commits | Interpretation |
| -------------------------------------- | ------- | -------------- |
| `GitHub <noreply@github.com>`          | 14      | GitHub's web-flow committer identity for squash/merge commits made through the ToadAid account; every one of these commits is authored by `ToadAid <ToadaidDAO@gmail.com>` and carries a PR reference (`#3`–`#14`). |
| `ToadAid <ToadaidDAO@gmail.com>`       | 2       | Directly created commits (`3384465` "bootstrap A2A repository", `780ed9b` governed work-market blueprint). |

Conclusion: **no commit in this repository has a committer or author other than the
ToadAid account** (directly, or via GitHub's own web-flow committer acting for that
account). There is no evidence of third-party contributed code. (No `gh` call was
needed; `git log` alone supplied this evidence.)

### 3.2 Vendoring checks — upstream code and text are NOT vendored

- The repository's 58 tracked files are all ToadAid-authored: Python modules
  (`agent_web/`, `observatory/`, `tools/`, `tests/`), JSON contracts and schemas under
  `contracts/`, Markdown docs, and two GitHub Actions workflows. Total ~9,242 lines.
- `contracts/agent-web/a2a-upstream-v1.0.1.json` contains **only metadata** about
  `a2aproject/A2A` release `v1.0.1`: the upstream name, release tag, release commit SHA,
  paths and Git blob SHA-1s of the normative proto and spec docs, a verification date,
  and explicit false flags (`externalConformanceTestPassed: false`,
  `publicDeploymentAuthorized: false`). It does not contain any upstream code or text.
- `contracts/agent-web/a2a-tck-pin-20261030.json` likewise contains only a **metadata
  pin** for `a2aproject/a2a-tck` (pinned commit, tree SHA, runner/project/lockfile paths
  and blob SHAs, verified date, explicit false flags).
- No file in the repository contains the text of the A2A `a2a.proto`, the upstream
  `specification.md`, or any upstream test code. No third-party license file, notice
  header, or attribution block is present anywhere in the tracked tree.
- The only place upstream sources are *used* is
  `.github/workflows/manual-a2a-tck-qualification.yml`, which clones
  `a2aproject/a2a-tck` at run time on a GitHub-hosted runner to a disposable
  `$RUNNER_TEMP` directory and verifies known Git object SHAs before running the TCK.
  This fetches upstream code on the runner; it does not vendor or redistribute it from
  this repository.
- The synthetic example files (`contracts/examples/*.json`, `contracts/agent-web/examples/*.json`)
  are explicitly fictional ToadAid-authored fixtures, bound to that status by test
  assertions and the JSON schemas.

### 3.3 Self-containedness

`python3 -m unittest discover -s tests -v` completed with **236 tests, OK**, using
standard-library Python 3 only — confirming the codebase has no third-party runtime
dependencies and nothing is hidden inside generated dependencies.

## 4. Proposed MIT scope (original work)

MIT (as drafted in the new `LICENSE` file at the repository root, with the copyright
line `Copyright (c) 2026 ToadAid` and no additional text) is proposed for the **entire
repository as it stands**, because every tracked file is ToadAid original work:

- `*.py` modules: `agent_web/`, `observatory/`, `tools/`, plus `tests/` and the
  workflow YAML files — original ToadAid implementation.
- `contracts/**` — original ToadAid contract/schema documents. The two upstream pins
  (`a2a-upstream-v1.0.1.json`, `a2a-tck-pin-20261030.json`) contain only factual
  metadata (names, SHAs, paths) about third-party projects; facts are not copyrightable
  expression and are safe to include under MIT.
- `docs/**`, `README.md` — original ToadAid documentation.
- Future additions proposed in this cut (`CONTRIBUTING.md`, the two community docs, the
  README "Want to build with us?" addition) — authored in this cut.

**Status of the new `LICENSE`: PROPOSED-PENDING-DIRECTOR-APPROVAL.** It must not be
committed, merged, or announced until the Director approves it; the file itself carries
no status text (that record lives in this document), so a rejected LICENSE can be simply
deleted.

## 5. Third-party notice obligations (precise, no overclaims)

Nothing currently in the tree requires an Apache-2.0 notice, because no upstream
Apache-licensed code or expressive text is stored in or distributed from this
repository. To keep that true, the following obligations are recorded:

1. **References only, today.** `a2a-upstream-v1.0.1.json` and `a2a-tck-pin-20261030.json`
   name `a2aproject/A2A` and `a2aproject/a2a-tck` as *reference points*, not sources of
   copied code. If ToadAid ever copies upstream code, proto definitions, spec text,
   documentation passages, or test material into this repository from either upstream —
   both of which are Apache-2.0 licensed — Apache-2.0 notice and attribution obligations
   follow, and MIT cannot be applied to those copied portions.
2. **Runtime-only upstream use.** The manual TCK workflow clones upstream sources onto
   an ephemeral GitHub runner; the resulting evidence artifacts (raw TCK reports) are
   products of unmodified upstream code and should not be relicensed by ToadAid. They
   are retained as raw evidence only.
3. **Names and identifiers.** Nothing in this assessment licenses the use of any
   upstream project's trademarks or names beyond the factual references described
   above; MIT covers *this* repository's own files only.
4. **No relicensing claim is made for third-party or third-party-adjacent material**
   (e.g. the external Tobyworld lore repository referenced by
   `contracts/agent-web/lore-source-inventory.v0.json`). Rights to that lore remain
   **UNKNOWN** per the P0-WEB-03A/03B1/03B2A cuts, and a future export of any of it
   would be a separate decision with its own licensing analysis — entirely outside this
   repository's MIT scope.

## 6. Recommendation

MIT is appropriate and safe for the current scope: all evidence supports every tracked
file being ToadAid original work, with upstream contacts limited to factual metadata
pins and a runtime runner-side clone. Apply `LICENSE` only after Director approval.

## 7. Explicit unresolved questions for the Director

1. **Legal-entity naming:** is "ToadAid" in `Copyright (c) 2026 ToadAid` the correct
   and final copyright-holder name, or should it read a formal legal entity name?
2. **Contact email:** commits carry the `ToadaidDAO@gmail.com` address (now public in
   commit metadata). No email address is stated in `LICENSE` (nothing extra in the file)
   or `CONTRIBUTING.md`. Is the Director comfortable with that, or should a separate
   designated security-disclosure address be published (currently only GitHub private
   messaging to the repository owner is offered)?
3. **Future vendoring policy:** should future cuts be allowed to vendor Apache-2.0
   upstream material at all, or must they instead continue the current metadata-pin
   pattern with runtime-only upstream use (recommendation: continue pinning)?
4. **Evidence-artifact licensing:** should `LICENSE` be stated to exclude future raw
   TCK evidence artifacts produced by unmodified upstream code, or is the current
   silent behavior acceptable until the first authorized TCK run?
5. **Timing:** confirm merge order — Director approval of `LICENSE` and this assessment
   is a precondition before any community announcement of the repository being
   open-source under MIT.