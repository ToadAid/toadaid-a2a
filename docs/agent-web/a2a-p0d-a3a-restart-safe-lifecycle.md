# A2A-P0D-A3A — restart-safe credential-lifecycle checkpoint (CUT-A2A-P0D-A3A-20261103)

**Status:** LOCAL SYNTHETIC ENGINE · NOT DEPLOYED · NOT A CREDENTIAL ISSUER · NOT
AN INDEPENDENT LIFECYCLE AUTHORITY. This is an offline executable
security-engine extension of [A2A-P0D-A2](a2a-p0d-a2-credential-lifecycle-enforcement.md)
(as qualified by R1, review 5756293645). No database, identity provider,
Portal account, external framework, network, Agent Card, or live agent is
connected here, and none is created.

## 1. Mission and the gap it closes

P0D-A2 explicitly disclosed that the gate's two security-state structures
— the per-identity lifecycle high-watermark (`_lifecycle_high_water`) and
the severe-status latch (`_lifecycle_severe`) — were IN-MEMORY ONLY: a
process restart lost them. A3A demonstrates, with a real database file
and ACTUAL close/reopen + NEW gate instances, that previously observed
credential generations, revocation epochs, and severe-status latches now
SURVIVE an ordinary process restart — as an explicitly provisioned
OPTIONAL mode; the in-memory mode is unchanged and remains the default.

Constitutional rules preserved verbatim:
`REVOCATION_OVERRIDES_PRIOR_APPROVAL` and
`A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY`.

## 2. What the checkpoint is — and is not

`admission/checkpoint.py` is a LOCAL, restart-safe record of what THIS
gate has OBSERVED, stored per FULL identity context
`(agentRef, tenantRef, ownerRef)`:

- `highCredentialGeneration` — highest source-reported credential
  generation ever observed;
- `highRevocationEpoch` — highest source-reported revocation epoch;
- `severeLatchEpoch` — highest epoch observed while the trusted source
  reported a SEVERE status (`revoked`/`disabled`); NULL until a severe
  observation occurs.

It is **NOT a credential issuer and NOT an independent lifecycle
authority.** Every admission still requires ALL FOUR P0D-A2 seams:
trusted caller verifier (R1-4), trusted registration adapter, CURRENT
trusted lifecycle source, and the trusted clock — plus the trusted R1
freshness window (300 s age / 30 s future skew, inclusive, no grace; a
stale observation never reaches the checkpoint). The checkpoint stores
HISTORICAL, locally recorded anti-rollback state ONLY; it can never
resurrect a credential the CURRENT trusted source refuses, and it is
never consulted to prove anything about an agent's CURRENT state.

It is **NOT durable message history.** The admission journal remains
metadata-only and IN-MEMORY in this cut. Committing a lifecycle
checkpoint does not record a delivery result and restores no replay
history; `SESSION_STATE_IS_RECONSTRUCTIBLE_FROM_JOURNAL` is a FUTURE
session cut and is NOT claimed here. The gap between a durable lifecycle
checkpoint and recorded delivery results is asserted by a dedicated test
(a restarted gate's journal is empty; delivery results exist nowhere on
disk).

No agent-provided request may write checkpoint state: the only writer is
the gate's lifecycle-enforcement path, which runs AFTER the trusted
source's record survived rebuild/tamper validation, exact identity-match,
and R1 freshness. No request keys, message bodies, prompts, credentials,
signing keys, private reasoning, or wallets have any column to enter —
each row holds exactly three bounded identifiers and three bounded
integers (schema asserted by tests).

## 3. Checkpoint schema (versioned)

SQLite, standard-library only (`sqlite3`, `os`) — no new dependency
beyond Python's standard library:

```sql
CREATE TABLE checkpoint_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    kind TEXT NOT NULL,            -- "toadaid-a2a-lifecycle-checkpoint"
    schemaVersion TEXT NOT NULL    -- "0.1.0"
);
CREATE TABLE lifecycle_checkpoint (
    agentRef TEXT NOT NULL,
    tenantRef TEXT NOT NULL,
    ownerRef TEXT NOT NULL,
    highCredentialGeneration INTEGER NOT NULL,
    highRevocationEpoch INTEGER NOT NULL,
    severeLatchEpoch INTEGER,      -- NULL until first severe observation
    PRIMARY KEY (agentRef, tenantRef, ownerRef)
);
```

All fields use exact, bounded validation: identifiers must match
`^[a-z][a-z0-9-]{2,63}$`; counters are bounded non-negative integers
(booleans refuse). `schemaVersion` ("0.1.0") and `kind` are checked at
open time (unsupported schema → `CHECKPOINT_SCHEMA_UNSUPPORTED`; foreign
kind → the same; missing/garbage structure → `CHECKPOINT_CORRUPT`;
malformed rows → `CHECKPOINT_RECORD_MALFORMED`).

## 4. Explicit provisioning and fail-closed operation

Two separated modes:

1. **Synthetic in-memory mode (default, unchanged):** no checkpoint
   injected → the gate keeps its exact P0D-A2 behavior (existing tests
   prove backward compatibility; a parity test re-proves the in-memory
   latch).
2. **Persistent-checkpoint mode:** the trusted operator explicitly
   injects a `LifeCycleCheckpoint` via the gate's `trusted_checkpoint`
   seam. Provisioning is an explicit trusted-operator action
   (`provision_checkpoint(path)`) using synthetic test identities into a
   temporary RESTRICTED directory (tests chmod 0o700). It refuses an
   existing file (never overwrites or migrates), relative paths, missing
   parent directories, directories, and symlinks — including symlinked
   ANCESTOR components — (`CHECKPOINT_PATH_NOT_ADMITTED`). It also
   refuses any NONCANONICAL path spelling (R1-A, review 5757900441):
   POSIX resolves a symlink component BEFORE "..", so the previous
   normalize-then-walk order let `<dir>/link/../x.sqlite` validate as
   `<dir>/x.sqlite` while the kernel actually opened the location the
   symlink pointed at. The smallest deterministic correction is to
   require canonical form before any normalization. Nothing ever
   writes into production directories, system services, or existing
   application databases.

In persistent mode, ALL of the following REFUSE (`ParticipationRefused`
at the gate): no checkpoint DB (`CHECKPOINT_NOT_PROVISIONED`), invalid
schema (`CHECKPOINT_SCHEMA_UNSUPPORTED`), corrupt database
(`CHECKPOINT_CORRUPT`), malformed records (`CHECKPOINT_RECORD_MALFORMED`),
failed transaction / failed commit / busy deadline / read-only file /
closed checkpoint (`CHECKPOINT_WRITE_FAILED`), stale lifecycle
observation (`LIFECYCLE_OBSERVATION_STALE`, unchanged), missing trusted
lifecycle source (`LIFECYCLE_SOURCE_NOT_TRUSTED`, unchanged). There is
NEVER a silent fall-back to an empty in-memory checkpoint — a dedicated
test closes the checkpoint and proves the gate refuses until it is
reprovided.

## 5. Atomic security-state persistence

The key requirement is honored exactly: **validated security observations
are durably committed BEFORE an admission result can be returned.**
`apply_observation(agent_ref, tenant_ref, owner_ref, observed_status,
observed_generation, observed_epoch)` — the ONLY write path — runs, in
ONE transaction begun with `BEGIN IMMEDIATE`:

1. resolves the exact full identity context;
2. loads its prior checkpoint state (or none);
3. REJECTS counter rollback — an observed generation or epoch below the
   recorded maximum refuses `CREDENTIAL_STATE_ROLLBACK` with NO state
   change (identical policy code to the in-memory gate);
4. enforces the severe-status reactivation rule — a `registered`
   observation at an epoch NOT strictly newer than `severeLatchEpoch`
   refuses `LIFECYCLE_REACTIVATION_NOT_CURRENT`; generation-only
   advancement cannot bypass it; suspension never latches;
5. computes the next maxima (a severe observation additionally raises
   `severeLatchEpoch` to the observed epoch);
6. COMMITS durably (`PRAGMA synchronous = FULL`, rollback-journal mode);
7. only then does the remaining admission path proceed — the gate's
   CURRENT-status refusals and decision-currency comparisons follow.

Ordering notes, deliberately matched to the R1 in-memory semantics:

- Status refusals happen AFTER the commit, so a NEWLY observed
  `revoked`/`disabled` status is recorded BEFORE its refusal is returned
  (verified the instant the exception propagates); the gate then raises
  `LIFECYCLE_STATUS_REVOKED`/`_DISABLED`.
- The reactivation refusal is raised AFTER the maxima commit, mirroring
  the in-memory gate where the watermark update precedes the latch
  refusal.
- Rollback refusal raises with NO change (the in-memory gate likewise
  leaves the watermark untouched on rollback).
- R1-B (review 5757900441): NO validation refusal may leave an open
  transaction holding the write lock. A refusal raised inside the
  transaction (e.g. a malformed pre-existing row discovered at
  read time) is rolled back before it propagates — the connection is
  left outside the transaction and an INDEPENDENT writer can acquire
  the lock immediately (tested). Refusals that deliberately ended
  their transaction first keep their exact semantics: the
  stale-counter branch commits its zero-change transaction before
  raising, and the reactivation rule runs after the commit. If even
  the ROLLBACK itself fails, the handle is DISPOSED deterministically
  (set unusable): a failed cleanup must never permit a later admission
  on an uncertain connection — every later call meets the closed-
  checkpoint refusal (`CHECKPOINT_WRITE_FAILED`), a guarantee pinned by
  a dedicated failure-path test.

### Transaction and concurrency model

- Durability: rollback-journal mode with `synchronous = FULL` — a
  committed observation survives an ordinary process restart; an
  interrupted / never-committed transaction is discarded by SQLite
  recovery and the prior committed state survives intact (tested).
- Concurrency: `BEGIN IMMEDIATE` takes the database write lock at
  transaction START, so the read-compare-write of steps 1–6 is one
  atomic unit serialized by the DATABASE ENGINE — never by a
  process-local Python lock. Two independently running gate instances
  sharing one checkpoint file CANNOT both authorize from an outdated
  snapshot: the second writer's transaction reads the first writer's
  committed state (a four-thread race test on one shared file proves
  serialization: every success observes the committed maximum, stale
  writers refuse, and the durable end state is exactly the global
  maximum).
- Multi-process qualification (deliberately distinct from the
  four-thread race): the same serialization is additionally proven
  across SEPARATE OS PROCESSES — fork children, each opening its OWN
  sqlite connection on the shared file. Four racing child processes
  apply interleaved epoch lanes on one shared checkpoint: stale
  writers are refused `CREDENTIAL_STATE_ROLLBACK` by the DATABASE
  ENGINE, the accepted lanes' maximum (epoch 11) is the final durable
  state, and a separate test holds `BEGIN IMMEDIATE` in a foreign
  process to prove the applicant refuses `CHECKPOINT_WRITE_FAILED`
  under cross-process lock contention and makes progress after
  release. This is a claim about atomic compare-and-update on ONE
  shared file on one machine — NOT about multi-host coordination
  (no network coordination exists; different hosts must not share
  one checkpoint file).
- A busy deadline (`busy_timeout`, trusted-operator configured, bounded
  ≤ 60 s) yields `CHECKPOINT_WRITE_FAILED` — refuse, never guess.

## 6. Restart recovery evidence (scenarios A–F, all automated)

All scenarios use REAL sqlite files, ACTUAL `close()`/reopen, and NEW
`RegisteredAgentGate` instances (A–D also prove "no journal entries"
on every refusal):

- **A. Rotation:** observe gen 3 → persist → restart → source reports
  gen 2 → `CREDENTIAL_STATE_ROLLBACK`, no admission.
- **B. Revocation:** registered@1 → revoked@2 (refusal, severe latch=2
  recorded BEFORE the refusal) → restart → registered@2 →
  `LIFECYCLE_REACTIVATION_NOT_CURRENT`.
- **C. Correct recovery:** after severe@2, restart, registered@3 with a
  matching fresh decision → ADMITTED; the old epoch-2 decision still
  refuses (`REVOCATION_EPOCH_STALE`).
- **D. Emergency disablement:** same restart sequence with `disabled`;
  no same-epoch recovery; generation-only advancement cannot bypass.
- **E. Suspension:** suspension remains distinct —
  `LIFECYCLE_STATUS_SUSPENDED`, NO severe record, and a trusted
  suspension→registered recovery at an unchanged epoch ADMITS after
  restart when every other admission condition passes (matching
  decision supplied).
- **F. Identity isolation:** two identities share one agentRef with
  different tenants/owners; the durable record of one never affects the
  other (epoch-3 record does not trip epoch-1 admission of the second
  identity; an identity-one severe latch does not contaminate identity
  two, before AND after restart); cross-tenant message delivery stays
  refused (`CROSS_TENANT_DELIVERY_REFUSED`, no journal entry).

## 7. Failure and attack controls (§7 of the mission, all tested)

Missing database; invalid schema version; foreign database kind; corrupt
database (garbage bytes → refuse to open, `CHECKPOINT_CORRUPT`);
truncated/malformed checkpoint records; invalid counters (booleans,
strings, negatives) and status vocabulary at the checkpoint boundary;
duplicate identity records (PRIMARY KEY, proven via raw SQL
`IntegrityError` with the module unaffected); wrong identity context
(bad identifiers refuse; the gate's exact identity-match still runs
first); read-only database (fresh handle → `CHECKPOINT_WRITE_FAILED`, no
admission); interrupted transaction (abandoned uncommitted write is
discarded; prior state intact after reopen); failed commit / writer
contention (a second instance holding the write lock starves the
applicant to `CHECKPOINT_WRITE_FAILED`, retry succeeds after commit);
concurrent updates (four racing instances, database-level
serialization); symlink and unsafe-path handling (symlink target,
symlinked ancestors, relative paths, missing parents, directories,
re-provision attempts all refuse).

Failure injection never yields a successful admission receipt: every
persistence-failure test asserts the refusal AND an empty journal.

**Trust limitation (disclosed, demonstrated, NOT assumed away):** a
dedicated test deliberately performs a privileged whole-database rollback
— copying an older VALID checkpoint file over the current one — and the
rewind SUCCEEDS. SQLite provides atomic local transactions and ordinary
restart durability ONLY. It CANNOT establish that the database was not
maliciously replaced with an older valid copy. NO protection is claimed
from privileged host tampering, deliberate whole-database rollback,
storage loss, or compromised trusted sources; those require external
trust or recovery mechanisms that do not exist in this offline prototype.

**Path-check race (disclosed, honestly assessed):** the path-safety
checks run BEFORE the database is opened and are NOT atomic with the
open. A privileged local process that swaps the validated path for
another file (e.g. a symlink, or an older VALID database) inside the
check-vs-open window is not prevented — the same trust boundary as the
whole-database-rollback limitation: no protection is claimed against
privileged host tampering. A racing SWAP TO A FOREIGN or corrupt file,
by contrast, is caught at open-time verification
(`CHECKPOINT_SCHEMA_UNSUPPORTED` / `CHECKPOINT_CORRUPT`). R1-A removed
the normalize-then-walk ordering FLAW (a `symlink/..` component can no
longer hide the symlink from validation; canonical form is required
first — regression-tested, and provisioning through a rejected
noncanonical path creates NOTHING in either the expected or the
redirected location), but the check-vs-open TOCTOU race itself REMAINS
unsolved: no protection is claimed against privileged host tampering.

## 8. Preserved boundaries

The P0D-A2 gate continues to enforce, unchanged and fully covered by the
preserved 386-test suite: trusted caller authentication; independent
registration decisions; CURRENT lifecycle source verification; the
trusted clock with the 300 s freshness bound and 30 s future-skew limit;
send/receive scope separation; sender AND recipient lifecycle checks;
full identity-context binding; cross-tenant refusal; replay-after-
revocation refusal (replays cannot bypass the durable latch either);
all-false execution-authority flags on every receipt.

The journal is NOT durable in this cut. Its independent persistence and
session reconstruction belong to a later P0D-A3 stage
(`SESSION_STATE_IS_RECONSTRUCTIBLE_FROM_JOURNAL` — future cut, not
claimed here). The journal remains metadata-only and in-memory, and the
gap between committing a lifecycle checkpoint and recording a delivery
result is explicitly tested: a lifecycle checkpoint carries no delivery
results, and a restarted gate has no replay history.

## 9. Files

New: `admission/checkpoint.py`, `tests/test_a2a_p0d_restart_checkpoint.py`
(this document). Modified (narrow): `admission/gate.py` (docs,
constructor seam, durable branch in `_enforce_lifecycle`; the in-memory
path is byte-identical), `admission/__init__.py` (docs only). No
modifications to existing lifecycle tests were required (none deleted,
none weakened; no existing assertion changed).

NOT modified: Observatory contracts, Gemini dashboard worktree, community
issues #17–#19, canonical A2A architecture, existing protocol pins,
Portal/MCP, Agent0 Diamond OS, production authentication or
infrastructure.

## 10. Verification

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` →
**428 tests OK** (386 baseline preserved + 42 new:
`CheckpointContractTests` 8, `RestartRotationTests` 1, `RestartRevocationTests` 2,
`RestartRecoveryTests` 1, `RestartDisablementTests` 1, `RestartSuspensionTests` 1,
`IdentityIsolationPersistenceTests` 2, `PersistenceFailureTests` 10,
`DurabilityBoundaryTests` 3, `InMemoryModeParityTests` 1,
`MultiprocessConcurrencyTests` 2 — the last two added in response to the
Director's multi-process review question: separate OS processes, fork
context, each child opening its own connection on the shared file;
`R1APathCanonTests` 5 and `R1BTransactionCleanupTests` 5 — security
hardening from independent review 5757900441, including the
rollback-failure disposal path demanded by the delivery inspection).
`git diff --check` clean. No secrets, no network services, no external
dependencies, no unapproved paths. All implementation changes remain
UNCOMMITTED; no GitHub writes; STOP before commit, push, PR, merge, or
deployment.

## 11. Remaining limitations (explicit, NOT assumed away)

- The durable checkpoint records only what THIS gate observed through
  the trusted source: revocations the source never reported between two
  observations remain invisible (unchanged limitation).
- No protection from privileged host tampering, deliberate
  whole-database rollback (demonstrated), storage loss, or compromised
  trusted sources.
- The path-safety checks are NOT atomic with the database open (a
  check-vs-open swap race by a privileged local process is not
  prevented; a swap to a foreign/corrupt file is caught at open-time
  verification).
- The journal is still IN-MEMORY and metadata-only; delivery results are
  NOT durable; replay history is NOT restored on restart.
- Timestamp validation remains non-cryptographic (P0D-A2 disclosure).
- GATE_STATUS remains `LOCAL_SYNTHETIC_ENGINE_NOT_DEPLOYED`; production
  provisioning is a future, Director-ruled decision.