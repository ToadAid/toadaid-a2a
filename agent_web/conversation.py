"""A2A-GEM-005: Deterministic conversation handlers and multi-turn exchange engine."""
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


def run_conversation_between_ports(
    port_a,
    port_b,
    session_id="session-pond-1",
    initial_prompt=POND_PROMPT_INITIAL,
    max_turns=4,
    correlation_id="corr-pond-1",
):
    """Execute a multi-turn connected conversation across two agent servers.

    Returns (turns_list, transcript_string).
    """
    turns = []
    current_prompt = initial_prompt
    last_msg_id = None

    for turn_idx in range(1, max_turns + 1):
        if turn_idx % 2 == 1:
            # Odd turns: Agent A -> Agent B
            sender = "agent-a"
            recipient = "agent-b"
            speaker_label = "Agent A"
            cred = "fixture-caller-a"
            dest_port = port_b
            src_port = port_a
        else:
            # Even turns: Agent B -> Agent A
            sender = "agent-b"
            recipient = "agent-a"
            speaker_label = "Agent B"
            cred = "fixture-caller-b"
            dest_port = port_a
            src_port = port_b

        msg_id = f"msg-turn-{turn_idx}"
        req = create_envelope_turn(
            sender=sender,
            recipient=recipient,
            seq=turn_idx,
            mid=msg_id,
            text=current_prompt,
            session_id=session_id,
            correlation_id=correlation_id,
            in_reply_to=last_msg_id,
        )

        # 1. Send to destination agent server
        status_dest, resp_dest = post_envelope_rpc(dest_port, req, cred=cred)
        if status_dest != 200:
            err = resp_dest.get("error", {}).get("message", "unknown error")
            raise RuntimeError(f"Turn {turn_idx} failed on destination {recipient}: {err}")

        # 2. Record outgoing on source agent server for sequence synchronization
        status_src, resp_src = post_envelope_rpc(src_port, req, cred=cred)
        if status_src != 200:
            err = resp_src.get("error", {}).get("message", "unknown error")
            raise RuntimeError(f"Turn {turn_idx} failed on source {sender}: {err}")

        turns.append((speaker_label, current_prompt))
        last_msg_id = msg_id

        # Destination response contains the synthetic handler's answer for the next turn
        reply_message = resp_dest.get("result", {}).get("message", {})
        reply_parts = reply_message.get("parts", [])
        if reply_parts and "text" in reply_parts[0]:
            current_prompt = reply_parts[0]["text"]

    transcript = format_transcript(turns)
    return turns, transcript


def main(argv=None):
    """Run an autonomous 4-turn demonstration between two agent subprocesses."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_a = Path(tmp_dir) / "agent-a"
        dir_b = Path(tmp_dir) / "agent-b"
        provision_conversation_session(dir_a, "session-pond-1", max_turns=10)
        provision_conversation_session(dir_b, "session-pond-1", max_turns=10)

        proc_a = subprocess.Popen(
            [sys.executable, "-m", "agent_web.local_probe", "--journal-dir", str(dir_a), "--port", "0", "--agent-id", "agent-a"],
            stdout=subprocess.PIPE,
            text=True,
        )
        port_a = None
        for line in proc_a.stdout:
            if "LOCAL_ONLY_NOT_DEPLOYED" in line:
                port_a = int(line.split("http://127.0.0.1:")[1].split("/")[0])
                break

        proc_b = subprocess.Popen(
            [sys.executable, "-m", "agent_web.local_probe", "--journal-dir", str(dir_b), "--port", "0", "--agent-id", "agent-b"],
            stdout=subprocess.PIPE,
            text=True,
        )
        port_b = None
        for line in proc_b.stdout:
            if "LOCAL_ONLY_NOT_DEPLOYED" in line:
                port_b = int(line.split("http://127.0.0.1:")[1].split("/")[0])
                break

        try:
            _, transcript = run_conversation_between_ports(port_a, port_b, max_turns=4)
            print(transcript)
            return 0
        finally:
            proc_a.terminate()
            proc_a.wait()
            proc_b.terminate()
            proc_b.wait()


if __name__ == "__main__":
    raise SystemExit(main())
