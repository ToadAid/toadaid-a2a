"""CUT-A2A-P0D-A1-20261103 — universal registered-agent admission gate.

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
  * Every admission binds agent identity, owner/controller, tenant, status,
    credential generation, revocation epoch, evidence expiry and the exact
    A2A participation scope. None of these implies another automatically.
  * Admitted messages carry ZERO execution authority (tools, payments,
    wallets, deployments, protected-host mutation, registration changes).
    Journal records hold metadata digests only — never message bodies.

NOT DEPLOYED. No public Agent Card, no external endpoint, no production
gateway, no production authentication. The journal is IN-MEMORY state —
not durable storage — and a restored hash chain proves tamper-evidence
only, never the authenticity of externally supplied history. The pinned upstream A2A contracts and the loopback probe are kept
elsewhere, untouched. Synthetic adapters in tests are explicitly labeled.
"""