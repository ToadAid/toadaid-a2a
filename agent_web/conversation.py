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
    endpoints=None,
):
    """Provision sessions.json in an agent journal directory with bounded maxTurns."""
    path = Path(journal_dir)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    
    parts = {
        participant_a: {"agentId": participant_a},
        participant_b: {"agentId": participant_b},
    }
    if endpoints:
        for p, url in endpoints.items():
            if p in parts:
                parts[p]["endpointUrl"] = url
                
    session_config = {
        session_id: {
            "sessionId": session_id,
            "state": "OPEN",
            "participants": parts,
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
    """Reconstruct [(speaker, text), ...] from explicitly temporary transcript file."""
    transcript_path = Path(journal_path).parent / "transcript.jsonl"
    if not transcript_path.exists():
        return []
        
    lines = transcript_path.read_text().splitlines()
    turns_with_seq = []
    for line in lines:
        try:
            event = json.loads(line)
            turns_with_seq.append((event["seq"], event["speaker"], event["text"]))
        except Exception:
            pass
            
    seen = set()
    unique = []
    for turn in turns_with_seq:
        if turn[0] not in seen:
            seen.add(turn[0])
            unique.append(turn)
            
    unique.sort(key=lambda x: x[0])
    return [(t[1], t[2]) for t in unique]


def run_autonomous_conversation_subprocesses(
    dir_a,
    dir_b,
    session_id="session-pond-1",
    max_turns=4,
    timeout_seconds=5.0,
):
    """Launch Agent A and Agent B as separate local processes without an external coordinator."""
    import socket
    def get_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
            
    port_a = get_free_port()
    port_b = get_free_port()
    
    url_a = f"http://127.0.0.1:{port_a}/a2a"
    url_b = f"http://127.0.0.1:{port_b}/a2a"
    endpoints = {"agent-a": url_a, "agent-b": url_b}
    
    provision_conversation_session(dir_a, session_id, max_turns, endpoints=endpoints)
    provision_conversation_session(dir_b, session_id, max_turns, endpoints=endpoints)

    proc_b = subprocess.Popen(
        [
            sys.executable, "-m", "agent_web.local_probe",
            "--journal-dir", str(dir_b),
            "--port", str(port_b),
            "--agent-id", "agent-b",
            "--autonomous",
            "--session-id", session_id,
        ],
        stdout=subprocess.PIPE, text=True,
    )

    proc_a = subprocess.Popen(
        [
            sys.executable, "-m", "agent_web.local_probe",
            "--journal-dir", str(dir_a),
            "--port", str(port_a),
            "--agent-id", "agent-a",
            "--autonomous",
            "--initiate",
            "--session-id", session_id,
        ],
        stdout=subprocess.PIPE, text=True,
    )

    try:
        deadline = time.time() + timeout_seconds
        journal_a = Path(dir_a) / "local-probe-events.jsonl"
        journal_b = Path(dir_b) / "local-probe-events.jsonl"
        
        while time.time() < deadline:
            def count_delivered(journal_path):
                if not journal_path.exists(): return 0
                lines = journal_path.read_text().splitlines()
                c = 0
                for line in lines:
                    try:
                        event = json.loads(line)
                        if event.get("response", {}).get("state") == "DELIVERED":
                            c += 1
                        elif event.get("response", {}).get("replied") is True:
                            c += 1
                    except Exception: pass
                return c
                
            c_a = count_delivered(journal_a)
            c_b = count_delivered(journal_b)
            # A sends 2 turns, B sends 2 turns. So each has 2 DELIVERED outbounds and 2 replies. 4 events total per agent.
            if c_a >= max_turns and c_b >= max_turns:
                break
            time.sleep(0.05)
            
        if c_a < max_turns or c_b < max_turns:
            raise RuntimeError(f"Timeout waiting for conversation to complete (A: {c_a}, B: {c_b})")

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
