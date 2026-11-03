"""CUT-A2A-P0D-A3A-20261103 — restart-safe credential-lifecycle checkpoint.

P0D-A2 (R1) left the admission gate's two security-state structures —
the per-identity lifecycle high-watermark and the severe-status latch —
IN-MEMORY ONLY, explicitly refusing to claim protection across a process
restart. This module closes that gap with a LOCAL, restart-safe
checkpoint of independently OBSERVED anti-rollback state, keyed by the
full identity context (agentRef, tenantRef, ownerRef), persisted with
Python's standard-library sqlite3 and nothing else.

What the checkpoint IS — and is NOT:
  * It is a durable record of what THIS GATE has observed: the highest
    source-reported credential generation, the highest source-reported
    revocation epoch, and the highest epoch ever observed while the
    trusted source reported a SEVERE status ("revoked"/"disabled") —
    per identity, atomically committed BEFORE the remaining admission
    path may proceed.
  * It is NOT a credential issuer, NOT an independent lifecycle
    authority, and NEVER a substitute for the CURRENT trusted lifecycle
    source. Every admission still requires all four P0D-A2 seams
    (trusted caller verifier, registration adapter, CURRENT lifecycle
    source, trusted clock) plus the R1 freshness window. The
    checkpoint stores HISTORICAL locally recorded anti-rollback state
    only; it can never resurrect a credential the CURRENT source
    refuses.
  * It is NOT durable MESSAGE history. The admission journal remains
    metadata-only and IN-MEMORY in this cut; committing a lifecycle
    checkpoint does not record any delivery result and restores NO
    replay history (SESSION_STATE_IS_RECONSTRUCTIBLE_FROM_JOURNAL is a
    FUTURE session cut, not claimed here).
  * It is NOT tamper-proof. SQLite provides atomic local transactions
    and ordinary-crash durability ONLY. It cannot establish that the
    database was not maliciously replaced with an older valid copy, and
    it claims NO protection from privileged host tampering, deliberate
    whole-database rollback, storage loss, or compromised trusted
    sources. Those require external trust or recovery mechanisms that
    do not exist in this offline prototype.

Constitutional rules (enforced, not decorative):
  * REVOCATION_OVERRIDES_PRIOR_APPROVAL — a severe-status observation is
    durably recorded BEFORE its refusal is returned, so the gate it was
    observed-at and a restarted gate both refuse same-epoch
    reactivation from then on.
  * No agent-provided request may write checkpoint state: the ONLY
    writer is the gate's lifecycle enforcement path, and it runs AFTER
    the trusted source's record survived rebuild/tamper, exact
    identity-match and R1 freshness validation. No request keys, no
    message bodies, no prompts, no credentials, no signing keys, no
    private reasoning, and no wallets have any column to enter. Each
    row holds three bounded identifiers and three bounded integers.

Fail-closed operation (PERSISTENT MODE ONLY; the in-memory mode of the
P0D-A2 gate is unchanged and stays the default):
  * No checkpoint / missing database -> refusal (provisioning is an
    explicit trusted-operator action; the checkpoint never creates or
    upgrades a schema by itself).
  * Unsupported schema version, foreign database, corrupt database,
    malformed checkpoint records, failed transaction, failed commit,
    read-only database / write failure, closed checkpoint -> refusal.
  * Refusal codes: CHECKPOINT_NOT_PROVISIONED, CHECKPOINT_PATH_NOT_
    ADMITTED, CHECKPOINT_SCHEMA_UNSUPPORTED, CHECKPOINT_CORRUPT,
    CHECKPOINT_RECORD_MALFORMED, CHECKPOINT_IDENTITY_NOT_ADMITTED,
    CHECKPOINT_COUNTER_NOT_ADMITTED, CHECKPOINT_WRITE_FAILED — plus the
    two REUSED policy codes LIFECYCLE_REACTIVATION_NOT_CURRENT and
    CREDENTIAL_STATE_ROLLBACK (identical policy, now durable). All
    surface at the gate as ParticipationRefused; a persistence failure
    can never produce a successful admission receipt.

Atomicity and concurrency:
  * Every observation is applied inside ONE SQLite transaction begun
    with BEGIN IMMEDIATE: the read of prior state, the counter-rollback
    comparison, the reactivation comparison and the write are one
    atomic unit, serialized by the database engine — never by a
    process-local Python lock. Two independently running gate
    instances sharing one checkpoint file therefore cannot BOTH
    authorize from an outdated snapshot: the second writer's
    transaction sees the first writer's committed state. A busy
    deadline (trusted-operator configured, bounded) yields
    CHECKPOINT_WRITE_FAILED rather than a stale decision.
  * Multi-process evidence: the serialization above is demonstrated by
    tests with SEPARATE OS PROCESSES (fork context, each child opening
    its own connection on the shared file), not only by in-process
    threads — the database engine's cross-process write lock provides
    the serialization. This is a claim about atomic compare-and-update
    on one shared file; it is NOT a claim about multi-host
    coordination (different hosts must not share one checkpoint file
    on different filesystems, and no network coordination exists).
  * Durability settings: journal-rollback mode with synchronous=FULL —
    a committed observation survives an ordinary process restart; an
    interrupted/uncommitted transaction is discarded by SQLite recovery
    and the prior committed state survives intact.

Path-validation limit (disclosed honestly): the path-safety checks
(absolute path, no symlink file or symlinked ancestor, existing
filesystem entry refused) run BEFORE the database is opened. They are
NOT atomic with the open. A privileged local process that swaps the
validated path for another file (e.g. a symlink or a valid older
database) inside that check-vs-open window is NOT prevented — this is
the same trust boundary as the whole-database-rollback limitation
below: no protection is claimed against privileged host tampering.

SYNTHETIC OFFLINE ONLY: temporary restricted directories in tests are
the only sanctioned locations. Nothing here is wired to production, no
production directory, system service, or application database is used,
and no other dependency beyond the standard library is introduced.
"""

import os
import sqlite3

from observatory.model import (
    IDENTIFIER_RE,
    MAX_INT_VALUE,
)

__all__ = [
    "CHECKPOINT_KIND",
    "CHECKPOINT_SCHEMA_VERSION",
    "DEFAULT_CHECKPOINT_BUSY_TIMEOUT_MS",
    "MAX_CHECKPOINT_BUSY_TIMEOUT_MS",
    "CheckpointRefused",
    "LifeCycleCheckpoint",
    "provision_checkpoint",
]

CHECKPOINT_KIND = "toadaid-a2a-lifecycle-checkpoint"
CHECKPOINT_SCHEMA_VERSION = "0.1.0"

# Busy deadline defaults/m bound (trusted-operator configuration; never
# request-provided).
DEFAULT_CHECKPOINT_BUSY_TIMEOUT_MS = 5000
MAX_CHECKPOINT_BUSY_TIMEOUT_MS = 60000

_CHECKPOINT_TABLES = ("checkpoint_meta", "lifecycle_checkpoint")

_SCHEMA_SQL = """
CREATE TABLE checkpoint_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    kind TEXT NOT NULL,
    schemaVersion TEXT NOT NULL
);
CREATE TABLE lifecycle_checkpoint (
    agentRef TEXT NOT NULL,
    tenantRef TEXT NOT NULL,
    ownerRef TEXT NOT NULL,
    highCredentialGeneration INTEGER NOT NULL,
    highRevocationEpoch INTEGER NOT NULL,
    severeLatchEpoch INTEGER,
    PRIMARY KEY (agentRef, tenantRef, ownerRef)
);
"""

_META_SELECT = ("SELECT kind, schemaVersion FROM checkpoint_meta "
                "WHERE singleton = 1")


class CheckpointRefused(PermissionError):
    """A checkpoint operation that cannot be authorized or performed.

    Raised ONLY by the checkpoint module; the gate maps it 1:1 onto
    ParticipationRefused so that every checkpoint refusal is an
    admission refusal first and a storage complaint second. args[0] is
    always an exact UPPER_SNAKE refusal code.
    """


def _pin_identifier(value):
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise CheckpointRefused("CHECKPOINT_IDENTITY_NOT_ADMITTED")


def _pin_counter(value):
    if isinstance(value, bool) or not isinstance(value, int) \
            or value < 0 or value > MAX_INT_VALUE:
        raise CheckpointRefused("CHECKPOINT_COUNTER_NOT_ADMITTED")


def _pin_status(value):
    if value not in ("registered", "suspended", "revoked", "disabled"):
        raise CheckpointRefused("CHECKPOINT_STATUS_NOT_ADMITTED")


def _pin_row(agent_ref, tenant_ref, generation, epoch, severe):
    """Exact, bounded validation of one persisted checkpoint row."""
    _pin_identifier(agent_ref)
    _pin_identifier(tenant_ref)
    if isinstance(generation, bool) or not isinstance(generation, int) \
            or not 0 <= generation <= MAX_INT_VALUE \
            or isinstance(epoch, bool) or not isinstance(epoch, int) \
            or not 0 <= epoch <= MAX_INT_VALUE:
        raise CheckpointRefused("CHECKPOINT_RECORD_MALFORMED")
    if severe is not None \
            and (isinstance(severe, bool) or not isinstance(severe, int)
                 or not 0 <= severe <= MAX_INT_VALUE):
        raise CheckpointRefused("CHECKPOINT_RECORD_MALFORMED")


def _safe_db_path(path):
    """Validate the database location BEFORE opening anything.

    Refuses: non-strings, empty/oversized paths, NUL bytes, relative
    paths (provisioning is an explicit trusted-operator action against
    a stated absolute location), missing parent directory, directories,
    and symlinks — including any symlinked ANCESTOR component, so a
    planted link cannot redirect checkpoint writes into production
    storage.
    """
    if not isinstance(path, str) or not path or len(path) > 4096 \
            or "\x00" in path:
        raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED")
    if not os.path.isabs(path):
        raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED")
    probe = os.path.normpath(path)
    while True:
        if os.path.islink(probe):
            raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED")
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    if not os.path.isfile(path) and os.path.isdir(path):
        raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED")
    if not os.path.isdir(os.path.dirname(path)):
        raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED")
    return path


def _open_connection(path, busy_timeout_ms):
    try:
        connection = sqlite3.connect(path, isolation_level=None)
    except sqlite3.Error as exc:
        raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED") from exc
    try:
        connection.execute("PRAGMA busy_timeout = %d" % busy_timeout_ms)
        connection.execute("PRAGMA synchronous = FULL")
    except sqlite3.DatabaseError as exc:
        # A foreign/corrupt file typically surfaces on the first real
        # read — report corruption, never a storage complaint.
        connection.close()
        raise CheckpointRefused("CHECKPOINT_CORRUPT") from exc
    except sqlite3.Error as exc:
        connection.close()
        raise CheckpointRefused("CHECKPOINT_WRITE_FAILED") from exc
    return connection


def provision_checkpoint(path,
                         busy_timeout_ms=DEFAULT_CHECKPOINT_BUSY_TIMEOUT_MS):
    """Explicit trusted-operator provisioning of a NEW checkpoint.

    Refuses an existing database (never overwrites, never migrates the
    schema of an occupied file), then creates the versioned schema and
    returns an OPEN checkpoint bound to it. The only sanctioned use is
    SYNTHETIC OFFLINE provisioning into a temporary, restricted
    directory — never a production directory, system service, or an
    existing application database.
    """
    _safe_db_path(path)
    if os.path.lexists(path):
        raise CheckpointRefused("CHECKPOINT_PATH_NOT_ADMITTED")
    if isinstance(busy_timeout_ms, bool) \
            or not isinstance(busy_timeout_ms, int) \
            or not 0 < busy_timeout_ms <= MAX_CHECKPOINT_BUSY_TIMEOUT_MS:
        raise CheckpointRefused("CHECKPOINT_COUNTER_NOT_ADMITTED")
    connection = _open_connection(path, busy_timeout_ms)
    try:
        connection.execute("BEGIN IMMEDIATE")
        # One CREATE per execute: executescript() would implicitly commit
        # the surrounding transaction, so the schema is built and the
        # meta row written inside a single explicit atomic transaction.
        for statement in _SCHEMA_SQL.split(";"):
            if statement.strip():
                connection.execute(statement)
        connection.execute(
            "INSERT INTO checkpoint_meta (singleton, kind, schemaVersion) "
            "VALUES (1, ?, ?)", (CHECKPOINT_KIND, CHECKPOINT_SCHEMA_VERSION))
        connection.execute("COMMIT")
    except sqlite3.Error as exc:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        connection.close()
        raise CheckpointRefused("CHECKPOINT_WRITE_FAILED") from exc
    except BaseException:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        connection.close()
        raise
    return LifeCycleCheckpoint._bound(connection, path, busy_timeout_ms)


class LifeCycleCheckpoint:
    """One open, restart-safe lifecycle checkpoint (sqlite3-backed).

    Holds, PER FULL IDENTITY CONTEXT (agentRef, tenantRef, ownerRef):
    the highest independently observed credential generation and
    revocation epoch, and the highest epoch observed in a SEVERE
    state. All writes go through apply_observation() — one atomic
    compare-and-update transaction per validated, FRESH lifecycle
    observation.
    """

    def __init__(self, path, busy_timeout_ms=DEFAULT_CHECKPOINT_BUSY_TIMEOUT_MS):
        """Open an EXISTING checkpoint file, fail-closed.

        There is no implicit creation, no implicit upgrade, and no
        fall-back to an empty in-memory checkpoint: a missing,
        foreign, unsupported-schema, corrupt, or malformed database
        refuses (CHECKPOINT_NOT_PROVISIONED / _SCHEMA_UNSUPPORTED /
        _CORRUPT / _RECORD_MALFORMED).
        """
        _safe_db_path(path)
        if isinstance(busy_timeout_ms, bool) \
                or not isinstance(busy_timeout_ms, int) \
                or not 0 < busy_timeout_ms <= MAX_CHECKPOINT_BUSY_TIMEOUT_MS:
            raise CheckpointRefused("CHECKPOINT_COUNTER_NOT_ADMITTED")
        if not os.path.isfile(path):
            raise CheckpointRefused("CHECKPOINT_NOT_PROVISIONED")
        self._path = path
        self._busy_timeout_ms = busy_timeout_ms
        self._connection = _open_connection(path, busy_timeout_ms)
        try:
            self._verify_schema()
        except BaseException:
            self._connection.close()
            self._connection = None
            raise

    @classmethod
    def _bound(cls, connection, path, busy_timeout_ms):
        """Bind an already-validated, provisioned connection."""
        checkpoint = object.__new__(cls)
        checkpoint._path = path
        checkpoint._busy_timeout_ms = busy_timeout_ms
        checkpoint._connection = connection
        return checkpoint

    # -- integrity ---------------------------------------------------------

    def _verify_schema(self):
        try:
            tables = self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            names = sorted(row[0] for row in tables
                           if not row[0].startswith("sqlite_"))
            checking = self._connection.execute(
                "PRAGMA integrity_check").fetchall()
        except sqlite3.DatabaseError as exc:
            raise CheckpointRefused("CHECKPOINT_CORRUPT") from exc
        except sqlite3.Error as exc:
            raise CheckpointRefused("CHECKPOINT_WRITE_FAILED") from exc
        if names != sorted(_CHECKPOINT_TABLES) \
                or [row[0] for row in checking] != ["ok"]:
            raise CheckpointRefused("CHECKPOINT_CORRUPT")
        try:
            meta = self._connection.execute(_META_SELECT).fetchall()
            rows = self._connection.execute(
                "SELECT agentRef, tenantRef, ownerRef, "
                "highCredentialGeneration, highRevocationEpoch, "
                "severeLatchEpoch FROM lifecycle_checkpoint").fetchall()
        except sqlite3.Error as exc:
            raise CheckpointRefused("CHECKPOINT_RECORD_MALFORMED") from exc
        if len(meta) != 1 \
                or meta[0][0] != CHECKPOINT_KIND \
                or meta[0][1] != CHECKPOINT_SCHEMA_VERSION:
            raise CheckpointRefused("CHECKPOINT_SCHEMA_UNSUPPORTED")
        for agent_ref, tenant_ref, owner_ref, generation, epoch, severe in rows:
            _pin_identifier(agent_ref)
            _pin_identifier(tenant_ref)
            _pin_identifier(owner_ref)
            _pin_row(agent_ref, tenant_ref, generation, epoch, severe)
        if len({(row[0], row[1], row[2]) for row in rows}) != len(rows):
            # A PRIMARY KEY violation cannot be introduced through the
            # module, but a tampered file must refuse anyway.
            raise CheckpointRefused("CHECKPOINT_RECORD_MALFORMED")

    # -- atomic observation -------------------------------------------------

    def apply_observation(self, agent_ref, tenant_ref, owner_ref,
                          observed_status, observed_generation,
                          observed_epoch):
        """Atomically compare-and-update for one VALIDATED, FRESH
        lifecycle observation.

        This is the ONLY write path. The caller (the gate's lifecycle
        enforcement) has already rebuilt, tamper-checked,
        identity-matched and freshness-checked the trusted source's
        record; this method re-validates the scalars it is handed,
        then, in ONE BEGIN IMMEDIATE transaction:

          1. loads the identity's prior checkpoint state (or None);
          2. REJECTS counter rollback (observed generation or epoch
             below the recorded maximum -> CREDENTIAL_STATE_ROLLBACK,
             no state change);
          3. computes the next maxima — a SEVERE observation
             ("revoked"/"disabled") additionally raises the
             severeLatchEpoch to the observed epoch;
          4. COMMITS the new row durably (synchronous=FULL);
          5. ONLY THEN applies the severe-status reactivation rule:
             a "registered" observation at an epoch not strictly newer
             than the severe latch refuses
             (LIFECYCLE_REACTIVATION_NOT_CURRENT) — after the commit,
             exactly mirroring the in-memory gate, where the watermark
             update precedes the latch refusal.

        Concurrency: BEGIN IMMEDIATE serializes writers at the
        DATABASE level (never a process-local lock), so two
        independently running gate instances sharing this file cannot
        both authorize from an outdated snapshot. A busy deadline
        raises CHECKPOINT_WRITE_FAILED — refuse, never guess.

        Returns the (newly) persisted state triple
        (highCredentialGeneration, highRevocationEpoch,
        severeLatchEpoch) for gate/test inspection.
        """
        if self._connection is None:
            raise CheckpointRefused("CHECKPOINT_WRITE_FAILED")
        _pin_identifier(agent_ref)
        _pin_identifier(tenant_ref)
        _pin_identifier(owner_ref)
        _pin_status(observed_status)
        _pin_counter(observed_generation)
        _pin_counter(observed_epoch)
        severe_observed = observed_epoch \
            if observed_status in ("revoked", "disabled") else None

        try:
            self._connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise CheckpointRefused("CHECKPOINT_WRITE_FAILED") from exc
        except sqlite3.Error as exc:
            raise CheckpointRefused("CHECKPOINT_CORRUPT") from exc

        prior_severe = None
        prior_seen = False
        try:
            row = self._connection.execute(
                "SELECT highCredentialGeneration, highRevocationEpoch, "
                "severeLatchEpoch FROM lifecycle_checkpoint WHERE "
                "agentRef = ? AND tenantRef = ? AND ownerRef = ?",
                (agent_ref, tenant_ref, owner_ref)).fetchone()
            if row is not None:
                prior_seen = True
                prior_generation, prior_epoch, prior_severe = row
                _pin_row(agent_ref, tenant_ref, prior_generation,
                         prior_epoch, prior_severe)
                if observed_generation < prior_generation \
                        or observed_epoch < prior_epoch:
                    self._connection.execute("COMMIT")
                    raise CheckpointRefused("CREDENTIAL_STATE_ROLLBACK")
            next_generation = observed_generation
            next_epoch = observed_epoch
            if prior_seen:
                next_generation = max(observed_generation, prior_generation)
                next_epoch = max(observed_epoch, prior_epoch)
            next_severe = severe_observed
            if prior_seen and prior_severe is not None:
                next_severe = max(next_severe, prior_severe) \
                    if next_severe is not None else prior_severe
            if row is None:
                self._connection.execute(
                    "INSERT INTO lifecycle_checkpoint (agentRef, tenantRef, "
                    "ownerRef, highCredentialGeneration, highRevocationEpoch, "
                    "severeLatchEpoch) VALUES (?, ?, ?, ?, ?, ?)",
                    (agent_ref, tenant_ref, owner_ref,
                     next_generation, next_epoch, next_severe))
            else:
                self._connection.execute(
                    "UPDATE lifecycle_checkpoint SET "
                    "highCredentialGeneration = ?, highRevocationEpoch = ?, "
                    "severeLatchEpoch = ? WHERE agentRef = ? AND "
                    "tenantRef = ? AND ownerRef = ?",
                    (next_generation, next_epoch, next_severe,
                     agent_ref, tenant_ref, owner_ref))
            self._connection.execute("COMMIT")
        except CheckpointRefused:
            raise
        except sqlite3.Error as exc:
            try:
                self._connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            if isinstance(exc, (sqlite3.OperationalError,
                                sqlite3.ProgrammingError)):
                raise CheckpointRefused("CHECKPOINT_WRITE_FAILED") from exc
            raise CheckpointRefused("CHECKPOINT_CORRUPT") from exc

        # Severe-status reactivation rule — ENFORCED AFTER the durable
        # commit: a refused reactivation still leaves the (equal-or-
        # higher) maxima recorded, exactly as the in-memory gate
        # refreshes the watermark before the latch refusal.
        if observed_status == "registered" and prior_seen \
                and prior_severe is not None \
                and observed_epoch <= prior_severe:
            raise CheckpointRefused("LIFECYCLE_REACTIVATION_NOT_CURRENT")
        return {
            "agentRef": agent_ref,
            "tenantRef": tenant_ref,
            "ownerRef": owner_ref,
            "highCredentialGeneration": next_generation,
            "highRevocationEpoch": next_epoch,
            "severeLatchEpoch": next_severe,
        }

    def checkpoint_state(self, agent_ref, tenant_ref, owner_ref):
        """Read-only inspection of one identity's recorded state."""
        _pin_identifier(agent_ref)
        _pin_identifier(tenant_ref)
        _pin_identifier(owner_ref)
        row = self._connection.execute(
            "SELECT highCredentialGeneration, highRevocationEpoch, "
            "severeLatchEpoch FROM lifecycle_checkpoint WHERE "
            "agentRef = ? AND tenantRef = ? AND ownerRef = ?",
            (agent_ref, tenant_ref, owner_ref)).fetchone()
        if row is None:
            return None
        _pin_row(agent_ref, tenant_ref, row[0], row[1], row[2])
        return {"highCredentialGeneration": row[0],
                "highRevocationEpoch": row[1],
                "severeLatchEpoch": row[2]}

    def close(self):
        """Close the underlying connection; later use refuses."""
        if self._connection is not None:
            self._connection.close()
        self._connection = None

    @property
    def path(self):
        return self._path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False