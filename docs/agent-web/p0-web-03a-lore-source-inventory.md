# P0-WEB-03A — exact-source lore inventory with publication HOLD

**Status: read-only, local developer proof · NOT DEPLOYED · NO REAL LORE REPUBLISHED.**  
**Cut:** CUT-P0-WEB-03A-20261030 · source snapshot **observation**, not a new canonical Reader generation.

## Source investigation and hierarchy

We inspected the existing public `ToadAid/toadaid-lore-reader` repository and the canonical public `ToadAid/toadaid.github.io` repository. The Reader's [source contract](https://github.com/ToadAid/toadaid-lore-reader/blob/main/docs/lore-reader-source-contract.md) states a permanent authored source identity:

- `ToadAid/toadaid.github.io` — `lore/data.json`.
- The **exact canonical commit** is *generation-specific*, must be reviewed and supplied as a full 40-character lowercase SHA, not hardcoded permanently.
- Reader imports use read-only Git plumbing to obtain `<commit>:lore/data.json`, never independently supplied source bytes or a mutable runtime `main`.
- Each record has stable `id`, `date`, `title`, and `comment`; `original`, `url`, `img`, `tags` are optional/possibly empty.
- `original` and `comment` stay separate. Archive `date` is a chronology marker, **not a verified publication timestamp**. Duplicate IDs fail closed.
- The Reader is a derived consumer, not an independently authored archive. A2A publishing cannot silently become a second authoritative lore repository.

**Observed public source at inspection, 2026-10-30:** canonical repository main commit `40ed594230395eafe6f233d1b27855181ec8dffe`; `lore/data.json` Git blob SHA-1 `b81d32c951d754780ac310e38b81a17f21292fe1`, JSON array with **132 records** and the eight fields above. This is **Git object evidence**, not a verified SHA-256 digest, rights clearance, completeness guarantee or lasting source pin. The Reader's historical example `LORE_SOURCE.example.json` represents an older 130-record generation; do not overwrite or reconcile its provenance automatically.

The canonical public GitHub repository did not advertise a GitHub license and no root `LICENSE` file was found in this inspection. **Absence of a license does not establish who owns rights**, but it also does not supply permission to redistribute content under an assumed open license. This cut marks text and media export **HOLD pending explicit rights and attribution review**, regardless of their existing public accessibility.

Read-only [architecture evidence](../../contracts/agent-web/lore-source-inventory.v0.json) records this observation and these limitations, but contains **no lore text, historical media or real-user identity**.

## New local-only tool: inventory, not export

`python3 -m agent_web.lore_provenance --canonical-repo /PATH/TO/REVIEWED/LOCAL/CANONICAL/CHECKOUT --commit <FULL_REVIEWED_SHA>`

- Accepts the existing **local** canonical checkout and an exact reviewed commit; no network, fetch, pull, clone, HTTP request, API or renderer is invoked.
- Fixes canonical repository and source path in code. The local checkout's `origin` must equal one of three expected GitHub URL spellings, but **a Git remote string is editable and cannot prove authentic GitHub ownership**.
- Resolves the exact reviewed commit, verifies that `lore/data.json` is a bounded Git blob and obtains bytes with read-only Git plumbing. Computes the source SHA-256 from those bytes.
- Validates record shape, non-empty required fields, optional string fields, duplicate IDs, JSON duplicate member names, UTF-8, finite JSON and a 2 MiB maximum.
- Emits **metadata only** (exact commit, Git blob, SHA-256 source digest, counts, rights HOLD). Never prints or writes record bodies, titles, original posts, comments, images or media URLs.
- The operator must independently verify the intended commit with the canonical maintainer before import. A malicious local repository can forge its `origin` and invent its own commit; the tool does not independently authenticate or attest the canonical author.
- The tool writes no files. It has no publication route, no rights-approval input, no registry, no Git write, no execution authority, no service activation.

Run the repository's stdlib tests with `python3 -m unittest discover -s tests -v`. Tests build **temporary synthetic local Git repositories** only. No real lore content is copied into the public A2A repository.

## Historic media caution

The Reader's [historical artifact contract](https://github.com/ToadAid/toadaid-lore-reader/blob/main/docs/historical-artifact-contract.md) explicitly says legacy `img` is a source reference **only**, not verified possession or preservation. The Reader's semantics require independently authored `rightsStatus` and governed expected digest before `PRESERVED_VERIFIED`. Merely counting an `img` field in this cut **must not** imply a binary exists, is legally reusable, has a valid hash, or was preserved. The A2A inventory never fetches media.

## Next independently authorized gate: P0-WEB-03B

Before any real content is republished on `agent.toadaid.org`:

1. Director selects a reviewed exact canonical source commit and independently validates its origin and Git object identity.
2. Source owner/rightsholder or authorized custodian records explicit rights scope, attribution, approved fields, intended audience, revocation/withdrawal process, and whether downstream redistribution is permitted. **Unknown rights means HOLD.**
3. Lore Reader importer semantics are retained: preserve canonical IDs, original/comment separation and archive chronology. Reconcile only through governed canonical updates, never through generated A2A edits.
4. Media links/artifacts are reviewed independently; source URLs never prove preservation or reuse rights.
5. After source/rights/privacy approval, produce a redacted, versioned local read-only export proof with negative controls. No public route before separate P0E deployment authorization.

**Official A2A TCK remains UNRUN**; this publishing cut is independent of protocol conformance and cannot satisfy that gate.

**Preserve the Lore · Empower the People · Build Together.**  
**ONE CUT · ONE PROOF · ONE DIRECTOR RULING.**
