# P0B-C2A — guarded manual upstream A2A TCK harness (not executed)

**Status:** execution infrastructure only · **OFFICIAL TCK NOT RUN** · **NO PUBLIC DEPLOYMENT**.  
**Cut:** CUT-P0B-C2A-20261030 · public repo: `ToadAid/toadaid-a2a`.

## Why this cut is preparatory

Our current P0B-B `agent_web.local_probe` is deliberately a narrow, fixed-response `SendMessage` subset, not a complete A2A server. It has passed its own local and cross-process tests; the independently maintained official A2A Technology Compatibility Kit (TCK) has **not** been run against it.

This cut creates a manual GitHub-hosted qualification harness. The reviewed PR and normal CI only test the harness and refusal conditions. **They do not execute TCK or prove A2A conformance.** An actual run requires a new Director authorization and an explicit `workflow_dispatch` from the repository's protected `main`.

## Source and scope pinned

Official A2A TCK repository `a2aproject/a2a-tck`, commit `d4d6fae7887f88ef607fb461c13e3b0e1802f19b`:
- Git tree SHA-1: `8469eb8aa083c027aa00a3107972b1787dc6671a`.
- `run_tck.py` Git blob SHA-1: `06f70520f89c2bb60e1f752694781141568ad08b`.
- `uv.lock` Git blob SHA-1: `9c17390a1441fb70d798baa8f4e71bc24fe95cdb`.
- `pyproject.toml` Git blob SHA-1: `3bb6059dbd68d3ce9e2dd01776077adebc7c5577`.

The [existing TCK pin](../../contracts/agent-web/a2a-tck-pin-20261030.json) remains the source of record. These are Git object hashes, **not** SHA-256 declarations. The workflow verifies every object before dependency installation. The A2A spec pin remains v1.0.1, with wire major/minor 1.0. Test kit and specification pins are separate.

The future manual run chooses **JSON-RPC** and **MUST** tests: `uv run --no-sync python run_tck.py --sut-host http://127.0.0.1:<port> --transport jsonrpc --level must`. This intentionally does not claim SHOULD/MAY, cross-transport, or external SDK qualification.

## Execution and isolation boundary

File: [manual-a2a-tck-qualification.yml](../../.github/workflows/manual-a2a-tck-qualification.yml).

The workflow:
1. Is **manual-only** and starts with a fail-closed, visible **first-step Director gate** checking both `main` and the exact acknowledgement `RUN_PINNED_TCK_LOCAL_ONLY`. A mismatched branch or approval exits nonzero **before checkout or third-party work**; it must not run on PR, push, or schedule.
2. Uses a short-lived GitHub-hosted `ubuntu-latest` runner, read-only repository token, disabled persistent checkout credentials, pinned setup/checkout/artifact actions and a pinned `uv` tool.
3. Clones the **public, pinned** upstream TCK at a fixed commit, checks the tree and the runner/lock/project Git object identities, then runs `uv sync --locked --no-dev`. This step downloads and executes **third-party dependencies** in the isolated runner; it is **not** permission to install them on Dell, TNG, or any production box.
4. Starts only the existing synthetic A2A probe bound to `127.0.0.1` with a temporary mode-0700 private journal directory. No public Agent Card, tunnel, external endpoint, Agent0, MCP, wallet, Portal registration, or protected host state is touched.
5. Runs upstream JSON-RPC MUST suite **without modifying/xfailing/skipping its mandatory tests to make them green**.
6. Collects raw stdout/stderr and upstream `compatibility.json`, `compatibility.html`, `tck_report.html`, `junitreport.xml` when emitted; preserves status and a bounded summary JSON in a seven-day GitHub Actions artifact even when the tests fail. The private server journal is **not uploaded**.
7. Stops the synthetic server. A failed TCK invocation **fails the workflow**, even though the evidence artifact remains available. A zero exit with absent, malformed, all-skipped, failing or errored JUnit evidence **also fails**.

### Truthful verdicts

`tools/tck_qualification_receipt.py` is an **evidence classifier**, not a certifier. It refuses incomplete reports, failures, zero tests or all-skipped suites and emits:
- `MUST_SUITE_FAIL_OR_EVIDENCE_HOLD` if the run failed or the evidence is incomplete.
- `MUST_SUITE_PROVISIONAL_PASS_DIRECTOR_REVIEW_REQUIRED` only for a zero exit and present, nontrivial successful reports.

Even a provisional MUST result is **not full protocol certification**, external SDK interoperability, production readiness, task-lifecycle completion, or authorization to serve a public Agent Card. The Director must review original reports, upstream code provenance, skipped MUST requirements, and safety implications before any next implementation cut.

### Expected result

Because our probe only supports a single bounded `SendMessage` shape, official MUST requirements may fail. This is useful **evidence of missing protocol features**. Do not edit the test suite, fake an Agent Card, or paper over a failure. Classify required repairs and cut them separately. If the TCK setup itself fails, record `INFRASTRUCTURE-HOLD`, not a protocol PASS/FAIL, until trustworthy evidence distinguishes them.

## Directors' separate launch instructions (not executed by this PR)

After merging and verifying post-merge CI, a Director may explicitly authorize running the manually triggered workflow on **main**, entering the exact gate string. The operator then reviews Actions run ID, run status, source commit, raw reports, the classification, and any tests skipped/failed. No background monitoring, automatic rerun, or force push. The first run's evidence should be recorded without altering private journals or real-world ToadAid resources.

**STOP:** if any upstream source identity differs, dependencies cannot be installed reproducibly, host scope changes, data leaks into artifacts, or the harness attempts public exposure.

**ONE CUT · ONE PROOF · ONE DIRECTOR RULING.**

## P0B-C2B gate diagnostics — first launch refused (2026-10-30)

The first Director launch, GitHub Actions run [#41118047825](https://github.com/ToadAid/toadaid-a2a/actions/runs/41118047825), targeted approved main `62f5dd79770fb97bf13fd7fe01f96c698e69563a`. GitHub reported the job **SKIPPED** before running any steps. The prior job-level expression was `github.ref == 'refs/heads/main' && inputs.director_gate == 'RUN_PINNED_TCK_LOCAL_ONLY'`. The branch was verified correct; the submitted input is not exposed through the available GitHub run metadata, so **the specific mismatch was not proven**. No TCK test, dependency installation, or compatibility artifact was produced.

**Remediation:** move the exact branch and Director acknowledgement checks into the *first executable shell step*, before checkout and any dependency installation. Inputs are passed through the environment, not evaluated as Bash source. A denied launch now reports a visible, generic GitHub error **without revealing the supplied input**. An approved launch proceeds to the same source-pinned, loopback-only TCK sequence. If the gate is denied, the evidence-artifact step is skipped; if the gate is approved and TCK later fails, the workflow still uploads raw failure reports.

This repair does **not** execute the official TCK and does not prove compatibility or authorize deployment. Normal PR CI tests the gate logic with synthetic environment values and the existing foundation suite; it never runs the TCK.

**Operator checkpoint:** after this patch merges with post-merge CI green, select **main** and input exactly `RUN_PINNED_TCK_LOCAL_ONLY` in a **new manual Actions dispatch**. Do not rerun the prior skipped job or guess at the underlying cause. If the next run fails, inspect the first failing step and its sanitized error before any further attempt. No blind retries, no additional authority.
