"""A2A-GEM-006: Deterministic conversation handlers and autonomous agent conversation loops."""
import argparse
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

from agent_web.envelope import _canonical_json, _hash_payload

POND_PROMPT_INITIAL = "Hello, Agent B. Welcome to Agent Pond!"


def pond_handler_b(text, sender_id="agent-a", recipient_id="agent-b"):
    """Deterministic conversation handler for Agent B."""
    if "Welcome to Agent Pond!" in text:
        return "Hello, Agent A. What shall we discuss?"
    elif "explore Tobyworld" in text:
        return "Let's begin at the Go Pond!"
    return f"Agent B heard: {text}"


def pond_handler_a(text, sender_id="agent-b", recipient_id="agent-a"):
    """Deterministic conversation handler for Agent A."""
    if "What shall we discuss?" in text:
        return "Let's explore Tobyworld."
    elif "begin at the Go Pond!" in text:
        return "Splendid! Lead the way to the Go Pond."
    return f"Agent A heard: {text}"


CONVERSATION_HANDLERS = {
    "agent-a": pond_handler_a,
    "agent-b": pond_handler_b,
}


def create_envelope_turn(
    sender,
    recipient,
    seq,
    mid,
    text,
    session_id="session-pond-1",
    correlation_id="corr-pond-1",
    in_reply_to=None,
    overrides=None,
):
    """Build a valid deterministic A2A envelope turn preserving all invariants."""
    now_ms = int(time.time() * 1000)
    content_parts = {"text": text, "mediaType": "text/plain"}
    if overrides and "contentParts" in overrides:
        content_parts = overrides["contentParts"]
    payload_hash = _hash_payload(content_parts)

    metadata = {
        "protocolVersion": "a2a-p1a-v0",
        "sessionId": session_id,
        "messageId": mid,
        "senderAgentId": sender,
        "recipientAgentId": recipient,
        "sequence": seq,
        "kind": "TURN",
        "correlationId": correlation_id,
        "createdAt": now_ms - 1000,
        "expiresAt": now_ms + 60000,
        "payloadHash": payload_hash,
    }
    if in_reply_to:
        metadata["inReplyTo"] = in_reply_to

    env = {
        "metadata": metadata,
        "contentParts": content_parts,
        "signature": f"synthetic_signature_for_{sender}",
        "authoritySource": "NONE",
        "executionEligible": False,
    }
    if overrides:
        env.update(overrides)

    return {
        "jsonrpc": "2.0",
        "id": f"jsonrpc-{seq}",
        "method": "SendMessage",
        "params": {"envelope": env},
    }


def provision_conversation_session(
    journal_dir,
    session_id="session-pond-1",
    max_turns=10,
    participant_a="agent-a",
    participant_b="agent-b",
):
    """Provision sessions.json in an agent journal directory with bounded maxTurns."""
    path = Path(journal_dir)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    session_config = {
        session_id: {
            "sessionId": session_id,
            "state": "OPEN",
            "participants": {
                participant_a: {"agentId": participant_a},
                participant_b: {"agentId": participant_b},
            },
            "maxMessageBytes": 8192,
            "maxTurns": max_turns,
            "currentSequence": 0,
            "seenMessageIds": {},
        }
    }
    (path / "sessions.json").write_text(json.dumps(session_config))


def format_transcript(turns):
    """Format [(speaker_label, text), ...] into a readable transcript string."""
    return "\n".join(f"{speaker}: {text}" for speaker, text in turns)


def post_envelope_rpc(port, payload, cred):
    """Send an envelope to an agent port via loopback HTTP."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        body = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "A2A-Version": "1.0",
        }
        if cred is not None:
            headers["Authorization"] = f"Bearer {cred}"
        conn.request("POST", "/a2a", body, headers)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, json.loads(raw.decode("utf-8"))
    finally:
        conn.close()


def extract_transcript_from_journal(journal_path):
    """Reconstruct [(speaker, text), ...] from a verified journal file."""
    lines = Path(journal_path).read_text().splitlines()
    turns = []
    for line in lines:
        try:
            event = json.loads(line)
            resp = event.get("response", {})
            seq = event.get("envelopeState", {}).get("sequence")
            if seq is None:
                continue
            speaker = "Agent A" if seq % 2 == 1 else "Agent B"
            if resp.get("outbound"):
                text = resp.get("text", "")
            else:
                text = resp.get("receivedText", "")
            turns.append((speaker, text))
        except Exception:
            pass
    # Sort strictly by sequence order if multiple events
    return turns


def run_autonomous_conversation_subprocesses(
    dir_a,
    dir_b,
    session_id="session-pond-1",
    max_turns=4,
    timeout_seconds=5.0,
):
    """Launch Agent A and Agent B as separate local processes without an external coordinator.

    Agent A initiates Turn 1. Turns 2-4 are constructed and dispatched autonomously by the agents.
    Returns (turns_list, transcript_string).
    """
    proc_b = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "agent_web.local_probe",
            "--journal-dir",
            str(dir_b),
            "--port",
            "0",
            "--agent-id",
            "agent-b",
            "--autonomous",
            "--session-id",
            session_id,
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    port_b = None
    for line in proc_b.stdout:
        if "LOCAL_ONLY_NOT_DEPLOYED" in line:
            port_b = int(line.split("http://127.0.0.1:")[1].split("/")[0])
            break

    if port_b is None:
        proc_b.terminate()
        raise RuntimeError("Failed to obtain ephemeral port for Agent B")

    proc_a = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "agent_web.local_probe",
            "--journal-dir",
            str(dir_a),
            "--port",
            "0",
            "--agent-id",
            "agent-a",
            "--peer-url",
            f"http://127.0.0.1:{port_b}/a2a",
            "--autonomous",
            "--initiate",
            "--session-id",
            session_id,
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    port_a = None
    for line in proc_a.stdout:
        if "LOCAL_ONLY_NOT_DEPLOYED" in line:
            port_a = int(line.split("http://127.0.0.1:")[1].split("/")[0])
            break

    if port_a is None:
        proc_a.terminate()
        proc_b.terminate()
        raise RuntimeError("Failed to obtain ephemeral port for Agent A")

    try:
        # Wait for both agents to complete max_turns in their journals
        deadline = time.time() + timeout_seconds
        journal_a = Path(dir_a) / "local-probe-events.jsonl"
        journal_b = Path(dir_b) / "local-probe-events.jsonl"
        while time.time() < deadline:
            lines_a = journal_a.read_text().splitlines() if journal_a.exists() else []
            lines_b = journal_b.read_text().splitlines() if journal_b.exists() else []
            if len(lines_a) >= max_turns and len(lines_b) >= max_turns:
                break
            time.sleep(0.05)

        turns = extract_transcript_from_journal(journal_a)
        transcript = format_transcript(turns)
        return turns, transcript

    finally:
        proc_a.terminate()
        proc_a.wait()
        proc_b.terminate()
        proc_b.wait()


def main(argv=None):
    """Run an autonomous 4-turn demonstration between two independent agent subprocesses."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_a = Path(tmp_dir) / "agent-a"
        dir_b = Path(tmp_dir) / "agent-b"
        provision_conversation_session(dir_a, "session-pond-1", max_turns=4)
        provision_conversation_session(dir_b, "session-pond-1", max_turns=4)

        _, transcript = run_autonomous_conversation_subprocesses(dir_a, dir_b, max_turns=4)
        print(transcript)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
