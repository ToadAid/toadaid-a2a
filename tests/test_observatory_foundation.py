"""CUT-AO-P0A-20261103 — offline, dependency-free Observatory qualification.

Synthetic, offline, stdlib-only tests for the Agent Observatory data
foundation: bounded model, evidence-class separation, owner-scoped read
boundary, tenant isolation, safe pagination, privacy redaction, and the
fail-closed default. No network, no socket servers, no secrets, no live
agents. Boundary under test: synthetic read-only observability foundation —
no public routes, no live authentication claims, NOT DEPLOYED.
"""

import copy
import json
import unittest

from observatory import contract as contract_module
from observatory import feed as feed_module
from observatory import model as model_module
from observatory.feed import (
    ALLOWED_PAGE_LIMITS,
    FeedRecorder,
    OwnerScopeTrustRefused,
    assert_public_directory_is_separate_cut,
    owner_dashboard_feed,
)
from observatory.model import (
    IDENTIFIER_RE,
    ObservatoryRefusal,
    build_event,
    canonical_json,
    canonical_json as _digest,
)

SECRET_TEXT = "raw-private-token-should-never-appear"


def authorize_alpha(scope):
    return scope["tenantRef"] == "tenant-alpha" and scope["ownerRef"] == "owner-alpha"


def recorder_with_alpha(*, capacity=feed_module.MAX_EVENTS):
    return FeedRecorder(capacity=capacity, trusted_authorization_adapter=authorize_alpha)


def identity_event(event_id="evt-alpha-001", evidence="infrastructure_observed",
                   agent_ref="agent-alpha-one", status="registered",
                   component="agent-admission-portal", tenant="tenant-alpha",
                   owner="owner-alpha", privacy="community",
                   visibility="operator", occurred="2026-11-03T00:00:00Z",
                   correlation="corr-alpha-001"):
    return build_event(
        event_kind="agent_identity_reference",
        event_id=event_id,
        correlation_id=correlation,
        occurred_at_utc=occurred,
        evidence_class=evidence,
        source_identity=component if evidence == "infrastructure_observed" else agent_ref,
        tenant_ref=tenant,
        owner_ref=owner,
        privacy_classification=privacy,
        visibility_class=visibility,
        payload={"agentRef": agent_ref, "registrationStatus": status},
    )


class ModelTests(unittest.TestCase):
    def test_valid_event_fixed_shape(self):
        event = identity_event()
        self.assertEqual(set(event), set(model_module.COMMON_KEYS))
        self.assertEqual(event["payload"]["agentRef"], "agent-alpha-one")
        self.assertTrue(all(flag is False for flag in event["authorityFlags"].values()))

    def test_canonical_json_deterministic(self):
        first = canonical_json(identity_event())
        second = canonical_json(identity_event())
        self.assertEqual(first, second)
        self.assertEqual(first, canonical_json(json.loads(first)))

    def test_identifier_regex_bounds(self):
        self.assertTrue(IDENTIFIER_RE.match("evt-alpha-001"))
        self.assertFalse(IDENTIFIER_RE.match("Evt-Alpha"))
        self.assertFalse(IDENTIFIER_RE.match("bad:id!"))
        self.assertFalse(IDENTIFIER_RE.match("ab"))
        self.assertTrue(IDENTIFIER_RE.match("a" * 64))
        self.assertFalse(IDENTIFIER_RE.match("a" * 65))

    def test_timestamps_and_ids_refused(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "TIMESTAMP_NOT_ISO_UTC"):
            identity_event(occurred="2026-11-03 00:00:00")
        with self.assertRaisesRegex(ObservatoryRefusal, "EVENT_ID_NOT_ADMITTED"):
            identity_event(event_id="EVT-BAD")
        with self.assertRaisesRegex(ObservatoryRefusal, "CORRELATION_ID_NOT_ADMITTED"):
            identity_event(correlation="")

    def test_no_kwargs_smuggling_of_authority(self):
        event = identity_event()
        builder = {
            "event_kind": event["eventKind"],
            "event_id": event["eventId"],
            "correlation_id": event["correlationId"],
            "occurred_at_utc": event["occurredAtUtc"],
            "evidence_class": event["evidenceClass"],
            "source_identity": event["sourceIdentity"],
            "tenant_ref": event["tenantRef"],
            "owner_ref": event["ownerRef"],
            "privacy_classification": event["privacyClassification"],
            "visibility_class": event["visibilityClass"],
            "payload": event["payload"],
        }
        # Extra claimed authority is structurally impossible: the builder's
        # signature is an exact whitelist with no **kwargs.
        with self.assertRaises(TypeError):
            build_event(claimedOnline=True, **builder)
        rebuilt = build_event(**builder)
        self.assertEqual(rebuilt, event)
        self.assertNotIn("publicationAuthorized", rebuilt)
        self.assertNotIn("deploymentAuthorized", rebuilt)
        self.assertFalse(any(rebuilt["authorityFlags"].values()))

    def test_payload_whitelist_exact(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "PAYLOAD_KEYS_NOT_ADMITTED"):
            build_event(
                event_kind="agent_identity_reference",
                event_id="evt-alpha-x", correlation_id="corr-alpha-x",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="infrastructure_observed",
                source_identity="agent-admission-portal",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"agentRef": "agent-alpha-one",
                         "registrationStatus": "registered",
                         "claimedOnline": True},
            )
        with self.assertRaisesRegex(ObservatoryRefusal, "REGISTRATION_STATUS_NOT_ADMITTED"):
            build_event(
                event_kind="agent_identity_reference",
                event_id="evt-alpha-x", correlation_id="corr-alpha-x",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="infrastructure_observed",
                source_identity="agent-admission-portal",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"agentRef": "agent-alpha-one", "registrationStatus": "online"},
            )


class EvidenceSeparationTests(unittest.TestCase):
    def test_human_receipt_requires_off_chat_channel(self):
        base = dict(
            event_kind="human_authorization_receipt",
            event_id="evt-auth-001", correlation_id="corr-auth-001",
            occurred_at_utc="2026-11-03T00:00:00Z",
            evidence_class="human_authorized",
            source_identity="independent-off-chat-human-process",
            tenant_ref="tenant-alpha", owner_ref="owner-alpha",
            privacy_classification="community", visibility_class="operator",
            payload={"decisionChannel": "independent-off-chat-human-process",
                     "decisionId": "dec-001", "subjectKind": "agent_enrollment",
                     "subjectRef": "agent-alpha-one"},
        )
        self.assertEqual(build_event(**base)["evidenceClass"], "human_authorized")
        bad = copy.deepcopy(base)
        bad["payload"] = dict(bad["payload"], decisionChannel="chat-message")
        with self.assertRaisesRegex(ObservatoryRefusal, "HUMAN_DECISION_CHANNEL_NOT_OFF_CHAT"):
            build_event(**bad)
        bad_source = copy.deepcopy(base)
        bad_source["source_identity"] = "agent-alpha-one"
        with self.assertRaisesRegex(ObservatoryRefusal, "HUMAN_DECISION_CHANNEL_NOT_OFF_CHAT"):
            build_event(**bad_source)

    def test_refusal_receipt_keeps_objection(self):
        event = build_event(
            event_kind="human_refusal_receipt",
            event_id="evt-ref-001", correlation_id="corr-ref-001",
            occurred_at_utc="2026-11-03T00:00:00Z",
            evidence_class="human_authorized",
            source_identity="independent-off-chat-human-process",
            tenant_ref="tenant-alpha", owner_ref="owner-alpha",
            privacy_classification="community", visibility_class="operator",
            payload={"decisionChannel": "independent-off-chat-human-process",
                     "decisionId": "dec-002", "subjectKind": "agent_task",
                     "subjectRef": "task-1", "objectionCode": "PRIVACY"},
        )
        self.assertEqual(event["payload"]["objectionCode"], "PRIVACY")
        with self.assertRaisesRegex(ObservatoryRefusal, "OBJECTION_CODE_NOT_ADMITTED"):
            build_event(
                event_kind="human_refusal_receipt",
                event_id="evt-ref-002", correlation_id="corr-ref-002",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="human_authorized",
                source_identity="independent-off-chat-human-process",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"decisionChannel": "independent-off-chat-human-process",
                         "decisionId": "dec-003", "subjectKind": "agent_task",
                         "subjectRef": "task-1", "objectionCode": "NOT_A_CODE"},
            )

    def test_tool_metadata_never_self_authorized(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "EVIDENCE_CLASS_CONFLICTS_WITH_EVENT_KIND"):
            build_event(
                event_kind="mcp_tool_request_metadata",
                event_id="evt-tool-001", correlation_id="corr-tool-001",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="agent_reported",
                source_identity="agent-alpha-one",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"toolName": "lore.read", "requestState": "authorized",
                         "authorizationGrantRef": None},
            )

    def test_lifecycle_events_require_infrastructure_or_unverified(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "EVIDENCE_CLASS_CONFLICTS_WITH_EVENT_KIND"):
            build_event(
                event_kind="lifecycle_security_event",
                event_id="evt-life-001", correlation_id="corr-life-001",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="human_authorized",
                source_identity="independent-off-chat-human-process",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"agentRef": "agent-alpha-one",
                         "lifecycleKind": "rotation", "generation": 2,
                         "revocationEpoch": 1},
            )
        lifecycle = build_event(
            event_kind="lifecycle_security_event",
            event_id="evt-life-001", correlation_id="corr-life-001",
            occurred_at_utc="2026-11-03T00:00:00Z",
            evidence_class="infrastructure_observed",
            source_identity="lifecycle-journal",
            tenant_ref="tenant-alpha", owner_ref="owner-alpha",
            privacy_classification="community", visibility_class="operator",
            payload={"agentRef": "agent-alpha-one",
                     "lifecycleKind": "revocation", "generation": 1,
                     "revocationEpoch": 2},
        )
        self.assertEqual(lifecycle["payload"]["lifecycleKind"], "revocation")

    def test_agent_reported_source_must_be_agent(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "AGENT_REPORTED_SOURCE_MUST_BE_THE_AGENT"):
            build_event(
                event_kind="agent_activity_event",
                event_id="evt-act-001", correlation_id="corr-act-001",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="agent_reported",
                source_identity="observatory-recorder",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"agentRef": "agent-alpha-one",
                         "activityKind": "status_declaration"},
            )


class FeedBoundaryTests(unittest.TestCase):
    def test_default_recorder_refuses_all_reads(self):
        recorder = FeedRecorder()  # no trusted adapter: fail closed
        scope = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha"}
        with self.assertRaisesRegex(OwnerScopeTrustRefused, "OWNER_SCOPE_AUTHORIZATION_REQUIRED"):
            owner_dashboard_feed(recorder, scope)

    def test_wrong_adapter_scope_refused(self):
        recorder = recorder_with_alpha()
        scope = {"tenantRef": "tenant-beta", "ownerRef": "owner-beta",
                 "authorizationId": "auth-beta"}
        with self.assertRaisesRegex(OwnerScopeTrustRefused, "OWNER_SCOPE_AUTHORIZATION_REFUSED"):
            owner_dashboard_feed(recorder, scope)

    def test_malformed_scope_refused(self):
        recorder = recorder_with_alpha()
        with self.assertRaisesRegex(OwnerScopeTrustRefused, "OWNER_SCOPE_AUTHORIZATION_REQUIRED"):
            owner_dashboard_feed(recorder, {"tenantRef": "tenant-alpha"})
        with self.assertRaisesRegex(OwnerScopeTrustRefused, "OWNER_SCOPE_AUTHORIZATION_REQUIRED"):
            owner_dashboard_feed(
                recorder,
                {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha", "impersonator": "x"})

    def test_recorder_for_isolated_by_scope(self):
        def authorize_beta(scope):
            return scope["tenantRef"] == "tenant-beta" and scope["ownerRef"] == "owner-beta"
        beta_recorder = FeedRecorder(
            capacity=feed_module.MAX_EVENTS, trusted_authorization_adapter=authorize_beta)
        beta_recorder.record(identity_event(
            event_id="evt-beta-001", tenant="tenant-beta", owner="owner-beta",
            agent_ref="agent-beta-one", correlation="corr-beta-001",
        ), "agent-admission-portal")
        for bad_scope in (
            {"tenantRef": "tenant-alpha", "ownerRef": "owner-beta",
             "authorizationId": "auth-beta"},
            {"tenantRef": "tenant-beta", "ownerRef": "owner-alpha",
             "authorizationId": "auth-beta"},
        ):
            with self.assertRaisesRegex(OwnerScopeTrustRefused, "OWNER_SCOPE_AUTHORIZATION_REFUSED"):
                owner_dashboard_feed(beta_recorder, bad_scope)
        beta_feed = owner_dashboard_feed(
            beta_recorder,
            {"tenantRef": "tenant-beta", "ownerRef": "owner-beta",
             "authorizationId": "auth-beta"})
        self.assertEqual(beta_feed["stats"]["totalForOwner"], 1)

    def test_owner_isolation_between_scopes(self):
        def authorize_all(scope):
            return True
        recorder = recorder_with_alpha()
        recorder.record(identity_event(), "agent-admission-portal")
        other = FeedRecorder(
            capacity=feed_module.MAX_EVENTS, trusted_authorization_adapter=authorize_all)
        other.record(identity_event(
            event_id="evt-beta-001", tenant="tenant-beta", owner="owner-beta",
            agent_ref="agent-beta-one", correlation="corr-beta-001",
        ), "agent-admission-portal")
        alpha_feed = owner_dashboard_feed(
            recorder,
            {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
             "authorizationId": "auth-alpha"})
        self.assertEqual(alpha_feed["stats"]["totalForOwner"], 1)
        self.assertTrue(all(item["payload"].get("agentRef", "agent-alpha-one")
                            == "agent-alpha-one" for item in alpha_feed["items"]))
        beta_recorder_feed = owner_dashboard_feed(
            other,
            {"tenantRef": "tenant-beta", "ownerRef": "owner-beta",
             "authorizationId": "auth-beta"})
        self.assertEqual(beta_recorder_feed["stats"]["totalForOwner"], 1)
        json_blob = json.dumps(beta_recorder_feed)
        self.assertNotIn("agent-alpha-one", json_blob)
        self.assertNotIn("tenant-alpha", json_blob)

    def test_idempotent_and_conflicting_records(self):
        recorder = recorder_with_alpha()
        event = identity_event()
        first = recorder.record(event, "agent-admission-portal")
        self.assertEqual(first, {"recorded": True, "eventId": "evt-alpha-001"})
        replay = recorder.record(copy.deepcopy(event), "agent-admission-portal")
        self.assertEqual(replay["recorded"], "idempotent")
        self.assertEqual(len(recorder.events()), 1)
        conflict = copy.deepcopy(event)
        conflict["payload"] = dict(event["payload"], registrationStatus="revoked")
        with self.assertRaisesRegex(ObservatoryRefusal, "DUPLICATE_EVENT_ID_CONFLICT"):
            recorder.record(conflict, "lifecycle-journal")

    def test_capacity_fails_closed(self):
        recorder = recorder_with_alpha(capacity=2)
        for index in (1, 2):
            recorder.record(identity_event(event_id=f"evt-alpha-c{index}",
                                           correlation=f"corr-alpha-c{index}"),
                            "lifecycle-journal")
        with self.assertRaisesRegex(ObservatoryRefusal, "FEED_CAPACITY_EXCEEDED"):
            recorder.record(identity_event(event_id="evt-alpha-c3",
                                           correlation="corr-alpha-c3"),
                            "lifecycle-journal")

    def test_recorder_component_whitelist(self):
        recorder = recorder_with_alpha()
        with self.assertRaisesRegex(ObservatoryRefusal, "RECORDER_COMPONENT_NOT_TRUSTED"):
            recorder.record(identity_event(), "unknown-component")
        with self.assertRaisesRegex(ObservatoryRefusal, "RECORDER_COMPONENT_NOT_TRUSTED"):
            recorder.record(identity_event(), "browser")

    def test_filter_and_pagination_keys_pinned(self):
        recorder = recorder_with_alpha()
        scope = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha"}
        with self.assertRaisesRegex(ObservatoryRefusal, "FILTER_KEYS_NOT_ADMITTED"):
            owner_dashboard_feed(recorder, scope, filters={"agentRef": None, "hack": 1})
        with self.assertRaisesRegex(ObservatoryRefusal, "PAGE_LIMIT_NOT_ADMITTED"):
            owner_dashboard_feed(recorder, scope, pagination={"limit": 5000})
        with self.assertRaisesRegex(ObservatoryRefusal, "PAGE_TOKEN_NOT_ADMITTED"):
            owner_dashboard_feed(recorder, scope, pagination={"pageToken": "evil"})
        with self.assertRaisesRegex(OwnerScopeTrustRefused, "OWNER_SCOPE_AUTHORIZATION_REFUSED"):
            owner_dashboard_feed(
                recorder,
                {"tenantRef": "tenant-beta", "ownerRef": "owner-beta",
                 "authorizationId": "auth-beta"},
                pagination={"limit": ALLOWED_PAGE_LIMITS[0]})


class FeedPaginationRoundTripTests(unittest.TestCase):
    def test_cursor_roundtrip_and_end(self):
        recorder = recorder_with_alpha()
        total = 35
        for index in range(total):
            recorder.record(identity_event(
                event_id=f"evt-alpha-p{index:03d}",
                correlation=f"corr-alpha-p{index:03d}",
            ), "lifecycle-journal")
        scope = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha"}
        pages = []
        token = None
        while True:
            params = {"limit": 25} if token is None else {"limit": 25, "pageToken": token}
            feed = owner_dashboard_feed(recorder, scope, pagination=params)
            pages.append(feed["items"])
            token = feed.get("nextPageToken")
            if token is None:
                break
            self.assertRegex(token, r"^cur:[0-9]{1,9}$")
        self.assertEqual(sum(len(p) for p in pages), total)
        self.assertEqual([len(p) for p in pages], [25, 10])
        seen = [item["eventId"] for p in pages for item in p]
        self.assertEqual(len(set(seen)), total)
        self.assertEqual(
            seen,
            sorted(seen))  # insertion order stability


class UnknownStatusProjectionTests(unittest.TestCase):
    def test_claimed_status_projects_unknown(self):
        recorder = recorder_with_alpha()
        recorder.record(identity_event(evidence="agent_reported",
                                       agent_ref="agent-alpha-claim",
                                       status="registered"), "lifecycle-journal")
        scope = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha"}
        feed = owner_dashboard_feed(recorder, scope)
        self.assertEqual(len(feed["items"]), 1)
        item = feed["items"][0]
        self.assertTrue(item["claimed"])
        self.assertEqual(item["payload"]["registrationStatus"], "unknown")
        self.assertEqual(item["claimedRegistrationStatus"], "registered")
        blob = json.dumps(feed)
        self.assertNotIn('"verified"', blob)
        self.assertNotIn("online", blob)
        self.assertNotIn("idle", blob)

    def test_unverified_evidence_projects_unknown(self):
        recorder = recorder_with_alpha()
        recorder.record(identity_event(evidence="unverified",
                                       agent_ref="agent-alpha-ghost",
                                       status="registered",
                                       component="unresolved-source"),
                        "lifecycle-journal")
        scope = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha"}
        item = owner_dashboard_feed(recorder, scope)["items"][0]
        self.assertFalse(item["claimed"])
        self.assertEqual(item["evidenceClass"], "unverified")
        self.assertEqual(item["payload"]["registrationStatus"], "unknown")


class PrivacyRedactionTests(unittest.TestCase):
    def test_privacy_floor_refused_at_construction(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "PRIVACY_EXCEEDS_REQUESTED_VISIBILITY_FLOOR"):
            identity_event(privacy="private", visibility="public")

    def test_recorder_rejects_tampered_validated_events(self):
        recorder = recorder_with_alpha()
        event = identity_event()
        event["authorityFlags"] = dict(event["authorityFlags"], executionAuthorized=True)
        with self.assertRaisesRegex(ObservatoryRefusal, "EVENT_RECORD_TAMPERED"):
            recorder.record(event, "agent-admission-portal")
        self.assertEqual(len(recorder.events()), 0)

    def test_secret_text_never_in_feed_output(self):
        recorder = recorder_with_alpha()
        try:
            recorder.record(identity_event(), "lifecycle-journal")
        except Exception:
            pass
        blob = json.dumps(owner_dashboard_feed(
            recorder,
            {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
             "authorizationId": "auth-alpha"}))
        self.assertNotIn(SECRET_TEXT, blob)


class PublicDirectoryHoldTests(unittest.TestCase):
    def test_public_directory_refused_in_this_cut(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "PUBLIC_DIRECTORY_SEPARATE_FUTURE_CUT"):
            assert_public_directory_is_separate_cut()


class ContractTests(unittest.TestCase):
    def test_contract_declares_private_dashboard_and_future_directory(self):
        contract = contract_module.interface_contract()
        self.assertEqual(
            contract["kind"], "toadaid-observatory-interface-contract")
        self.assertTrue(
            contract["proposedSurface"]["privateOwnerDashboard"]["ownerScoped"])
        self.assertFalse(
            contract["proposedSurface"]["publicAgentDirectory"]["includedInThisCut"])
        self.assertEqual(contract["authorizationSeam"]["defaultPolicy"], "refuse")
        self.assertTrue(contract["privacyContract"]["privateByDefault"])
        self.assertFalse(contract["authority"]["executionEligible"])
        blob = json.dumps(contract)
        self.assertNotIn(SECRET_TEXT, blob)

    def test_example_response_matches_feed_contract(self):
        example = contract_module.synthetic_dashboard_example()
        self.assertEqual(example["kind"], feed_module.DASHBOARD_KIND)
        self.assertEqual(
            example["status"], feed_module.DASHBOARD_STATUS)
        for item in example["items"]:
            self.assertIn("claimed", item)
            self.assertIn("evidenceClass", item)
        claimed_items = [i for i in example["items"] if i["claimed"]]
        self.assertTrue(claimed_items)
        blob = json.dumps(example)
        self.assertNotIn(SECRET_TEXT, blob)

    def test_example_file_matches_generated_example(self):
        with open("contracts/examples/synthetic-observatory-feed.v0.json",
                  encoding="utf-8") as fh:
            stored = json.load(fh)
        generated = contract_module.synthetic_dashboard_example()
        self.assertEqual(stored["kind"], generated["kind"])
        self.assertEqual(stored["tenantRef"], generated["tenantRef"])
        self.assertEqual(stored["items"], generated["items"])

    def test_schema_file_pins_kind_and_false_flags(self):
        with open("contracts/agent-web/observatory-feed.v0.schema.json",
                  encoding="utf-8") as fh:
            schema = json.load(fh)
        self.assertEqual(schema["properties"]["kind"]["const"],
                         feed_module.DASHBOARD_KIND)
        self.assertEqual(schema["properties"]["authorityFlags"]["$ref"],
                         "#/$defs/authorityFlags")
        flags = schema["$defs"]["authorityFlags"]["properties"]
        self.assertTrue(all(props["const"] is False for props in flags.values()))
        self.assertIn("agentRegistrationActive", flags)


if __name__ == "__main__":
    unittest.main()