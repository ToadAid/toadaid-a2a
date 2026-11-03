"""CUT-A2A-P0D-A1-20261103 — universal registered-agent admission gate.

P0D-A2 extends this package with a fourth fail-closed seam: a trusted
credential-lifecycle state source (admission.lifecycle) enforcing
REVOCATION_OVERRIDES_PRIOR_APPROVAL on every admission. P0D-A3A adds an
OPTIONAL, explicitly provisioned restart-safe checkpoint
(admission.checkpoint): historical locally recorded anti-rollback state
(high-watermarks and severe-status latches) durably committed by atomic
SQLite transactions BEFORE an admission result may be returned — never a
substitute for the CURRENT trusted lifecycle source, never durable
message history.

Framework-neutral A2A participation and message-routing core, independent
of the future website (the website belongs to Codex; nothing HTTP exists
here).

Fail-closed by construction:
  * No trusted registration adapter injected -> NO agent participates.
  * Registration decisions may ONLY come from an injected, independently
    verified adapter — never from an Agent Card, a message body, a browser
    claim, or a framework name. A claim of registration is not registration.
  * Registration is NOT authentication (R1-4): every authorize()/route()
    call additionally requires an opaque caller credential bound by an
    injected trusted caller-identity verifier to an independently
    verified principal. Self-asserted identity strings (in requests,
    cards, or bodies) authenticate no one; a None verifier refuses
    everything.
  * Credential lifecycle (P0D-A2, REVOCATION_OVERRIDES_PRIOR_APPROVAL):
    a registration decision does not prove its own currency. Every
    authorize()/route() call also fetches CURRENT lifecycle state for
    each participating agent from an injected trusted_lifecycle_source —
    independently verified, never from agent-supplied claims — and a
    decision must carry the CURRENT credential generation and revocation
    epoch. Revocation, suspension, and emergency disablement refuse
    delivery; revoked/disabled latch per identity (in-memory): only a
    strictly newer revocation epoch re-admits
    (LIFECYCLE_REACTIVATION_NOT_CURRENT); suspension recovery at an
    unchanged epoch stays legitimate. Lifecycle observations must be
    FRESH against the trusted clock (trusted gate limits: 300 s maximum
    age, 30 s future skew, inclusive boundaries); an identical replay
    after a revocation refuses and appends no journal entry; per-identity
    IN-MEMORY high-watermarks detect state rollback (non-durable across
    restart). Timestamp validation is not cryptographic evidence
    authentication. No lifecycle source means refusal.
  * Restart-safe checkpoint (P0D-A3A, OPTIONAL): with an explicitly
    provisioned durable checkpoint injected, every validated, FRESH
    lifecycle observation is atomically recorded before any admission
    result — including a severe status recorded BEFORE its refusal —
    so rotated generations, bumped epochs and severe-status latches
    survive an ordinary process restart. Missing / unsupported /
    corrupt / malformed checkpoint, failed transaction or commit, and
    closed connections all REFUSE; there is no silent fall-back to the
    empty in-memory mode. The checkpoint is not a lifecycle authority
    and not durable message history: the journal stays IN-MEMORY and
    metadata-only in this cut. SQLite atomicity covers local
    transactions and ordinary restarts only — not privileged host
    tampering, whole-database rollback, storage loss, or compromised
    trusted sources.
  * Every admission binds agent identity, owner/controller, tenant, status,
    credential generation, revocation epoch, evidence expiry and the exact
    A2A participation scope. None of these implies another automatically.
  * Admitted messages carry ZERO execution authority (tools, payments,
    wallets, deployments, protected-host mutation, registration changes).
    Journal records hold metadata digests only — never message bodies.

NOT DEPLOYED. No public Agent Card, no external endpoint, no production
gateway, no production authentication, no real lifecycle authority. The
journal and the lifecycle high-watermark are IN-MEMORY state — not
durable storage — and a restored hash chain proves tamper-evidence only,
never the authenticity of externally supplied history. The pinned
upstream A2A contracts and the loopback probe are kept elsewhere,
untouched. Synthetic adapters in tests are explicitly labeled.
"""