"""CUT-AO-P0A-20261103 (+ R1) — offline, dependency-free Observatory qualification.

Synthetic, offline, stdlib-only tests for the Agent Observatory data
foundation: bounded model, evidence-class separation, owner-scoped read
boundary, tenant isolation, safe pagination, privacy redaction, and the
fail-closed default. R1 adversarial regressions add: trusted producer
ingestion (component strings are not credentials), immutability of recorded
events against retained references, exact schema/example/feed agreement,
and strict per-kind metadata types with real calendar timestamps.

Boundary under test: synthetic read-only observability foundation —
no public routes, no live authentication claims, NOT DEPLOYED.
"""

import copy
import json
import re
import unittest

from observatory import contract as contract_module
from observatory import feed as feed_module
from observatory import model as model_module
from observatory.feed import (
    ALLOWED_PAGE_LIMITS,
    FeedRecorder,
    OwnerScopeTrustRefused,
    ProducerToken,
    ProducerTrustRefused,
    assert_public_directory_is_separate_cut,
    owner_dashboard_feed,
    synthetic_offline_authenticator,
)
from observatory.model import (
    IDENTIFIER_RE,
    ObservatoryRefusal,
    build_event,
    canonical_json,
    canonical_json as _digest,
)

SECRET_TEXT = "raw-private-token-should-never-appear"

TOKEN_PORTAL = ProducerToken("test-portal")
TOKEN_JOURNAL = ProducerToken("test-journal")


def authorize_alpha(scope):
    return scope["tenantRef"] == "tenant-alpha" and scope["ownerRef"] == "owner-alpha"


def synthetic_bindings(tenant="tenant-alpha", owner="owner-alpha",
                       agent_refs=("agent-alpha-claim",)):
    return {
        TOKEN_PORTAL: {
            "producerComponent": "agent-admission-portal",
            "evidenceClasses": frozenset(
                {"infrastructure_observed", "agent_reported", "unverified"}),
            "humanReceipts": False,
            "tenantRefs": {tenant},
            "ownerRefs": {owner},
            "agentRefs": set(agent_refs),
        },
        TOKEN_JOURNAL: {
            "producerComponent": "lifecycle-journal",
            "evidenceClasses": frozenset(
                {"infrastructure_observed", "unverified", "human_authorized"}),
            "humanReceipts": True,
            "tenantRefs": {tenant},
            "ownerRefs": {owner},
            "agentRefs": None,
        },
    }


def recorder_with_alpha(*, capacity=feed_module.MAX_EVENTS,
                        tenant="tenant-alpha", owner="owner-alpha"):
    return FeedRecorder(
        capacity=capacity,
        trusted_authorization_adapter=authorize_alpha,
        trusted_producer_authenticator=synthetic_offline_authenticator(
            synthetic_bindings(tenant=tenant, owner=owner)),
    )


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


def lifecycle_event(event_id="evt-life-001", tenant="tenant-alpha",
                    owner="owner-alpha", agent_ref="agent-alpha-one",
                    lifecycle_kind="rotation", generation=2, epoch=1):
    return build_event(
        event_kind="lifecycle_security_event",
        event_id=event_id,
        correlation_id="corr-life-x" + event_id[-1],
        occurred_at_utc="2026-11-03T00:00:00Z",
        evidence_class="infrastructure_observed",
        source_identity="lifecycle-journal",
        tenant_ref=tenant,
        owner_ref=owner,
        privacy_classification="community",
        visibility_class="operator",
        payload={"agentRef": agent_ref, "lifecycleKind": lifecycle_kind,
                 "generation": generation, "revocationEpoch": epoch},
    )


def conversation_event(event_id="evt-conv-001", turn_count=4,
                       participants=("agent-alpha-one", "agent-alpha-two"),
                       conversation_id="conv-alpha-001", tenant="tenant-alpha",
                       owner="owner-alpha", evidence="infrastructure_observed",
                       source="agent-admission-portal"):
    return build_event(
        event_kind="a2a_conversation_metadata",
        event_id=event_id,
        correlation_id="corr-conv-001",
        occurred_at_utc="2026-11-03T00:00:00Z",
        evidence_class=evidence,
        source_identity=source,
        tenant_ref=tenant,
        owner_ref=owner,
        privacy_classification="community",
        visibility_class="operator",
        payload={"conversationId": conversation_id, "turnCount": turn_count,
                 "participants": list(participants)},
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

    def test_timestamps_must_be_real_calendar_dates(self):
        # Regex-shaped but impossible values are refused (R1 finding 4).
        with self.assertRaisesRegex(ObservatoryRefusal, "TIMESTAMP_NOT_A_REAL_UTC_DATETIME"):
            identity_event(occurred="2026-02-30T00:00:00Z")
        with self.assertRaisesRegex(ObservatoryRefusal, "TIMESTAMP_NOT_A_REAL_UTC_DATETIME"):
            identity_event(occurred="2026-11-03T25:00:00Z")
        with self.assertRaisesRegex(ObservatoryRefusal, "TIMESTAMP_NOT_A_REAL_UTC_DATETIME"):
            identity_event(occurred="2026-11-03T12:61:00Z")
        self.assertEqual(identity_event(
            occurred="2026-11-03T12:00:00.123456Z"
        )["occurredAtUtc"], "2026-11-03T12:00:00.123456Z")

    def test_non_string_ids_and_timestamps_refused(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "EVENT_ID_NOT_ADMITTED"):
            identity_event(event_id=20261103)
        with self.assertRaisesRegex(ObservatoryRefusal, "TIMESTAMP_NOT_ISO_UTC"):
            identity_event(occurred=20261103000000)

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

    def test_typed_metadata_fields_refuse_wrong_types(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "TURN_COUNT_NOT_ADMITTED"):
            conversation_event(turn_count="7")  # string, not int
        with self.assertRaisesRegex(ObservatoryRefusal, "TURN_COUNT_NOT_ADMITTED"):
            conversation_event(turn_count=True)  # bool is not a counter
        with self.assertRaisesRegex(ObservatoryRefusal, "TURN_COUNT_NOT_ADMITTED"):
            conversation_event(turn_count=-1)
        with self.assertRaisesRegex(ObservatoryRefusal, "CONVERSATION_ID_NOT_ADMITTED"):
            conversation_event(conversation_id="")

    def test_participants_are_identifier_only_metadata(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "PARTICIPANTS_NOT_ADMITTED"):
            conversation_event(
                participants=("agent-alpha-one",
                              {"role": "raw-transcript-privately-shared"}))
        with self.assertRaisesRegex(ObservatoryRefusal, "PARTICIPANTS_NOT_ADMITTED"):
            conversation_event(participants=("Raw private transcript text",))
        with self.assertRaisesRegex(ObservatoryRefusal, "PARTICIPANTS_NOT_ADMITTED"):
            conversation_event(participants=())
        self.assertEqual(
            conversation_event()["payload"]["participants"],
            ["agent-alpha-one", "agent-alpha-two"])

    def test_lifecycle_kinds_and_counters_typed(self):
        with self.assertRaisesRegex(ObservatoryRefusal, "LIFECYCLE_KIND_NOT_ADMITTED"):
            lifecycle_event(lifecycle_kind="silent-upgrade")
        with self.assertRaisesRegex(ObservatoryRefusal, "LIFECYCLE_COUNTER_TYPE_NOT_ADMITTED"):
            lifecycle_event(generation="2")
        with self.assertRaisesRegex(ObservatoryRefusal, "LIFECYCLE_COUNTER_TYPE_NOT_ADMITTED"):
            lifecycle_event(epoch=True)
        with self.assertRaisesRegex(ObservatoryRefusal, "LIFECYCLE_COUNTER_TYPE_NOT_ADMITTED"):
            lifecycle_event(generation=1.5)
        with self.assertRaisesRegex(ObservatoryRefusal, "AGENT_REF_NOT_ADMITTED"):
            lifecycle_event(agent_ref="Bad_Ref")
        self.assertEqual(lifecycle_event()["payload"]["lifecycleKind"], "rotation")

    def test_human_receipt_identifiers_typed(self):
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
        with self.assertRaisesRegex(ObservatoryRefusal, "DECISION_ID_NOT_ADMITTED"):
            build_event(**dict(base, payload=dict(base["payload"], decisionId="D1")))
        with self.assertRaisesRegex(ObservatoryRefusal, "SUBJECT_REF_NOT_ADMITTED"):
            build_event(**dict(base, payload=dict(base["payload"], subjectRef=42)))
        self.assertTrue(build_event(**base))


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

    def test_default_recorder_refuses_all_writes(self):
        recorder = FeedRecorder()  # no trusted producer authenticator at all
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_AUTHENTICATION_REQUIRED"):
            recorder.record(identity_event(), TOKEN_PORTAL)

    def test_component_string_forgery_refused(self):
        # R1 finding 1: typing a trusted component name is not provenance.
        recorder = recorder_with_alpha()
        for forged in ("agent-admission-portal", "lifecycle-journal",
                       "observatory-recorder", "browser"):
            with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_AUTHENTICATION_REFUSED"):
                recorder.record(identity_event(), forged)
        self.assertEqual(len(recorder.events()), 0)

    def test_wrong_scope_read_refused(self):
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
            capacity=feed_module.MAX_EVENTS,
            trusted_authorization_adapter=authorize_beta,
            trusted_producer_authenticator=synthetic_offline_authenticator(
                synthetic_bindings(tenant="tenant-beta", owner="owner-beta",
                                   agent_refs=("agent-beta-claim",))))
        beta_recorder.record(identity_event(
            event_id="evt-beta-001", tenant="tenant-beta", owner="owner-beta",
            agent_ref="agent-beta-one", correlation="corr-beta-001",
        ), TOKEN_PORTAL)
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
        recorder.record(identity_event(), TOKEN_PORTAL)
        other = FeedRecorder(
            capacity=feed_module.MAX_EVENTS,
            trusted_authorization_adapter=authorize_all,
            trusted_producer_authenticator=synthetic_offline_authenticator(
                synthetic_bindings(tenant="tenant-beta", owner="owner-beta",
                                   agent_refs=("agent-beta-claim",))))
        other.record(identity_event(
            event_id="evt-beta-001", tenant="tenant-beta", owner="owner-beta",
            agent_ref="agent-beta-one", correlation="corr-beta-001",
        ), TOKEN_PORTAL)
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
        first = recorder.record(event, TOKEN_PORTAL)
        self.assertEqual(first, {"recorded": True, "eventId": "evt-alpha-001"})
        replay = recorder.record(copy.deepcopy(event), TOKEN_PORTAL)
        self.assertEqual(replay["recorded"], "idempotent")
        self.assertEqual(len(recorder.events()), 1)
        conflict = copy.deepcopy(event)
        conflict["payload"] = dict(event["payload"], registrationStatus="revoked")
        with self.assertRaisesRegex(ObservatoryRefusal, "DUPLICATE_EVENT_ID_CONFLICT"):
            recorder.record(conflict, TOKEN_PORTAL)

    def test_capacity_fails_closed(self):
        recorder = recorder_with_alpha(capacity=2)
        for index in (1, 2):
            recorder.record(identity_event(event_id=f"evt-alpha-c{index}",
                                           correlation=f"corr-alpha-c{index}"),
                            TOKEN_PORTAL)
        with self.assertRaisesRegex(ObservatoryRefusal, "FEED_CAPACITY_EXCEEDED"):
            recorder.record(identity_event(event_id="evt-alpha-c3",
                                           correlation="corr-alpha-c3"),
                            TOKEN_PORTAL)

    def test_producer_binding_shape_checked(self):
        # A binding missing a required field is refused at record time, and
        # so is a binding that tries to pass an untrusted component.
        for mutate in (lambda b: b[TOKEN_PORTAL].pop("ownerRefs"),
                       lambda b: b[TOKEN_PORTAL].update(producerComponent="browser")):
            broken = synthetic_bindings()
            mutate(broken)
            broken_recorder = FeedRecorder(
                trusted_authorization_adapter=authorize_alpha,
                trusted_producer_authenticator=synthetic_offline_authenticator(broken))
            with self.assertRaisesRegex(ObservatoryRefusal, "PRODUCER_BINDING_NOT_ADMITTED"):
                broken_recorder.record(identity_event(), TOKEN_PORTAL)
        self.assertEqual(len(recorder_with_alpha().events()), 0)

    def test_producer_bindings_enforced(self):
        recorder = recorder_with_alpha()

        # Journal producer cannot attest infrastructure observed at the
        # portal's component, and cannot attest agent-reported claims at
        # all (its binding carries neither the evidence class nor agents).
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_SOURCE_MISMATCH"):
            recorder.record(identity_event(), TOKEN_JOURNAL)
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_EVIDENCE_NOT_BOUND"):
            recorder.record(identity_event(evidence="agent_reported",
                                           agent_ref="agent-alpha-claim"),
                            TOKEN_JOURNAL)

        # Portal producer cannot relay human receipts and cannot attest
        # agents outside its binding.
        relay_bound = synthetic_bindings()
        # Explicit adversarial case: the producer binding admits the evidence
        # class but the producer was never bound for human receipt relay.
        relay_bound[TOKEN_PORTAL] = dict(
            relay_bound[TOKEN_PORTAL],
            evidenceClasses=frozenset({"infrastructure_observed", "agent_reported", "human_authorized"}),
            humanReceipts=False)
        relay_recorder = FeedRecorder(
            trusted_authorization_adapter=authorize_alpha,
            trusted_producer_authenticator=synthetic_offline_authenticator(relay_bound))
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_HUMAN_CHANNEL_NOT_BOUND"):
            relay_recorder.record(build_event(
                event_kind="human_refusal_receipt",
                event_id="evt-ref-101", correlation_id="corr-ref-101",
                occurred_at_utc="2026-11-03T00:00:00Z",
                evidence_class="human_authorized",
                source_identity="independent-off-chat-human-process",
                tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                privacy_classification="community", visibility_class="operator",
                payload={"decisionChannel": "independent-off-chat-human-process",
                         "decisionId": "dec-101", "subjectKind": "agent_task",
                         "subjectRef": "task-1", "objectionCode": "PRIVACY"},
            ), TOKEN_PORTAL)
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_AGENT_NOT_BOUND"):
            recorder.record(identity_event(evidence="agent_reported",
                                           agent_ref="agent-alpha-stranger",
                                           event_id="evt-str-102",
                                           correlation="corr-str-102"),
                            TOKEN_PORTAL)

        # Out-of-scope tenant or owner records are refused even when the
        # event itself is valid.
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_TENANT_NOT_BOUND"):
            recorder.record(identity_event(
                event_id="evt-ten-103", correlation="corr-ten-103",
                tenant="tenant-beta"), TOKEN_PORTAL)
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_OWNER_NOT_BOUND"):
            recorder.record(identity_event(
                event_id="evt-own-104", correlation="corr-own-104",
                owner="owner-beta"), TOKEN_PORTAL)
        self.assertEqual(len(recorder.events()), 0)

    def test_evidence_class_not_bound_refused(self):
        restricted = synthetic_bindings()
        restricted[TOKEN_PORTAL] = dict(
            restricted[TOKEN_PORTAL], evidenceClasses=frozenset({"unverified"}))
        recorder = FeedRecorder(
            trusted_authorization_adapter=authorize_alpha,
            trusted_producer_authenticator=synthetic_offline_authenticator(restricted))
        with self.assertRaisesRegex(ProducerTrustRefused, "PRODUCER_EVIDENCE_NOT_BOUND"):
            recorder.record(identity_event(), TOKEN_PORTAL)

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

    def test_insertion_order_is_the_documented_order(self):
        recorder = recorder_with_alpha()
        late = identity_event(event_id="evt-alpha-z1", correlation="corr-alpha-z1",
                              occurred="2026-11-04T00:00:00Z")
        early = identity_event(event_id="evt-alpha-z0", correlation="corr-alpha-z0",
                               occurred="2026-11-01T00:00:00Z")
        recorder.record(late, TOKEN_PORTAL)
        recorder.record(early, TOKEN_PORTAL)
        scope = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                 "authorizationId": "auth-alpha"}
        items = owner_dashboard_feed(recorder, scope)["items"]
        # Contract truthfulness (R1 finding 3): the feed returns recorder
        # insertion order, not a silent timestamp sort.
        self.assertEqual([item["eventId"] for item in items],
                         ["evt-alpha-z1", "evt-alpha-z0"])


class FeedPaginationRoundTripTests(unittest.TestCase):
    def test_cursor_roundtrip_and_end(self):
        recorder = recorder_with_alpha()
        total = 35
        for index in range(total):
            recorder.record(identity_event(
                event_id=f"evt-alpha-p{index:03d}",
                correlation=f"corr-alpha-p{index:03d}",
            ), TOKEN_PORTAL)
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


class FeedImmutabilityTests(unittest.TestCase):
    """R1 finding 2: accepted records survive every retained reference."""

    ALPHA_SCOPE = {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
                   "authorizationId": "auth-alpha"}

    def test_retained_reference_cannot_rewrite_history(self):
        recorder = recorder_with_alpha()
        event = identity_event()
        recorder.record(event, TOKEN_PORTAL)
        # Full-forge attempt through the caller's retained dict.
        event["evidenceClass"] = "human_authorized"
        event["ownerRef"] = "owner-beta"
        event["payload"]["registrationStatus"] = "revoked"
        event["payload"]["agentRef"] = "agent-evil-999"
        stored = recorder.events()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["evidenceClass"], "infrastructure_observed")
        self.assertEqual(stored[0]["ownerRef"], "owner-alpha")
        self.assertEqual(stored[0]["payload"]["registrationStatus"], "registered")
        self.assertEqual(stored[0]["payload"]["agentRef"], "agent-alpha-one")

    def test_nested_payload_reference_isolated(self):
        recorder = recorder_with_alpha()
        event = conversation_event()
        recorder.record(event, TOKEN_PORTAL)
        event["payload"]["participants"][0] = "agent-evil-999"
        event["payload"]["turnCount"] = 999999
        self.assertEqual(recorder.events()[0]["payload"]["participants"],
                         ["agent-alpha-one", "agent-alpha-two"])
        self.assertEqual(recorder.events()[0]["payload"]["turnCount"], 4)

    def test_events_view_mutation_is_local(self):
        recorder = recorder_with_alpha()
        recorder.record(identity_event(), TOKEN_PORTAL)
        view = recorder.events()
        view[0]["evidenceClass"] = "human_authorized"
        view[0]["payload"]["registrationStatus"] = "revoked"
        view[0]["authorityFlags"]["publicationAuthorized"] = True
        fresh = recorder.events()
        self.assertEqual(fresh[0]["evidenceClass"], "infrastructure_observed")
        self.assertEqual(fresh[0]["payload"]["registrationStatus"], "registered")
        self.assertFalse(any(fresh[0]["authorityFlags"].values()))

    def test_feed_items_mutation_is_local(self):
        recorder = recorder_with_alpha()
        recorder.record(conversation_event(), TOKEN_PORTAL)
        scope = self.ALPHA_SCOPE
        feed = owner_dashboard_feed(recorder, scope)
        item = feed["items"][0]
        item["evidenceClass"] = "human_authorized"
        item["payload"]["participants"][0] = "agent-evil-999"
        item["payload"]["turnCount"] = 999999
        refetched = owner_dashboard_feed(recorder, scope)["items"][0]
        self.assertEqual(refetched["evidenceClass"], "infrastructure_observed")
        self.assertEqual(refetched["payload"]["participants"],
                         ["agent-alpha-one", "agent-alpha-two"])
        self.assertEqual(refetched["payload"]["turnCount"], 4)
        # And the journal digest is untouched by any of it.
        stored = recorder.events()[0]
        record = build_event(**{
            "event_kind": stored["eventKind"], "event_id": stored["eventId"],
            "correlation_id": stored["correlationId"],
            "occurred_at_utc": stored["occurredAtUtc"],
            "evidence_class": stored["evidenceClass"],
            "source_identity": stored["sourceIdentity"],
            "tenant_ref": stored["tenantRef"], "owner_ref": stored["ownerRef"],
            "privacy_classification": stored["privacyClassification"],
            "visibility_class": stored["visibilityClass"],
            "payload": stored["payload"]})
        feed_again = owner_dashboard_feed(recorder, scope)["items"][0]
        self.assertEqual(feed_again["payload"]["conversationId"],
                         record["payload"]["conversationId"])


class UnknownStatusProjectionTests(unittest.TestCase):
    def test_claimed_status_projects_unknown(self):
        recorder = recorder_with_alpha()
        recorder.record(identity_event(evidence="agent_reported",
                                       agent_ref="agent-alpha-claim",
                                       status="registered"), TOKEN_PORTAL)
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
                                       component="agent-alpha-ghost"),
                        TOKEN_JOURNAL)
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
            recorder.record(event, TOKEN_PORTAL)
        self.assertEqual(len(recorder.events()), 0)

    def test_secret_text_never_in_feed_output(self):
        recorder = recorder_with_alpha()
        try:
            recorder.record(identity_event(), TOKEN_PORTAL)
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


# --- R1 finding 3: genuine schema conformance without external deps. -----

class SchemaMismatch(AssertionError):
    pass


def _resolve_ref(root, ref):
    assert ref.startswith("#/$defs/")
    return root["$defs"][ref.split("/")[-1]]


def validate_against_feed_schema(instance, schema, root=None):
    """Minimal draft-2020-12 subset validator covering the feed schema."""
    root = root if root is not None else schema
    if "$ref" in schema:
        validate_against_feed_schema(instance, _resolve_ref(root, schema["$ref"]), root)
        return
    if "type" in schema:
        expected = schema["type"]
        if expected == "integer":
            if isinstance(instance, bool) or not isinstance(instance, int):
                raise SchemaMismatch(f"integer expected, got {instance!r}")
        else:
            python_type = {"object": dict, "string": str,
                           "boolean": bool, "array": list}[expected]
            if not isinstance(instance, python_type):
                raise SchemaMismatch(f"{expected} expected, got {instance!r}")
    if "const" in schema and instance != schema["const"]:
        raise SchemaMismatch(f"const violated by {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaMismatch(f"enum violated by {instance!r}")
    if "pattern" in schema:
        if not isinstance(instance, str) or not re.search(schema["pattern"], instance):
            raise SchemaMismatch(f"pattern violated by {instance!r}")
    if "maxLength" in schema and isinstance(instance, str) \
            and len(instance) > schema["maxLength"]:
        raise SchemaMismatch("maxLength violated")
    if "minimum" in schema and isinstance(instance, int) \
            and instance < schema["minimum"]:
        raise SchemaMismatch("minimum violated")
    if "maxItems" in schema and isinstance(instance, list) \
            and len(instance) > schema["maxItems"]:
        raise SchemaMismatch("maxItems violated")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                raise SchemaMismatch(f"required key missing: {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    raise SchemaMismatch(f"additional property not allowed: {key}")
        for key, subschema in properties.items():
            if key in instance:
                validate_against_feed_schema(instance[key], subschema, root)
    if isinstance(instance, list) and "items" in schema:
        for item in instance:
            validate_against_feed_schema(item, schema["items"], root)


def load_feed_schema():
    with open("contracts/agent-web/observatory-feed.v0.schema.json",
              encoding="utf-8") as fh:
        return json.load(fh)


class SchemaConformanceTests(unittest.TestCase):
    def setUp(self):
        self.schema = load_feed_schema()

    def test_stored_example_conforms_to_schema(self):
        with open("contracts/examples/synthetic-observatory-feed.v0.json",
                  encoding="utf-8") as fh:
            stored = json.load(fh)
        validate_against_feed_schema(stored, self.schema)

    def test_generated_example_conforms_to_schema(self):
        example = contract_module.synthetic_dashboard_example()
        validate_against_feed_schema(example, self.schema)

    def test_live_feed_response_conforms_to_schema(self):
        recorder = recorder_with_alpha()
        recorder.record(identity_event(), TOKEN_PORTAL)
        recorder.record(conversation_event(event_id="evt-conv-002",
                                           turn_count=1), TOKEN_PORTAL)
        recorder.record(identity_event(evidence="agent_reported",
                                       agent_ref="agent-alpha-claim",
                                       event_id="evt-claim-003",
                                       correlation="corr-claim-003"), TOKEN_PORTAL)
        feed = owner_dashboard_feed(
            recorder,
            {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
             "authorizationId": "auth-alpha"},
            pagination={"limit": 10})
        validate_against_feed_schema(feed, self.schema)

    def test_schema_rejects_authority_flag_true(self):
        with open("contracts/examples/synthetic-observatory-feed.v0.json",
                  encoding="utf-8") as fh:
            forged = json.load(fh)
        forged["authorityFlags"]["executionAuthorized"] = True
        with self.assertRaises(SchemaMismatch):
            validate_against_feed_schema(forged, self.schema)

    def test_schema_rejects_unspecified_top_level_key(self):
        with open("contracts/examples/synthetic-observatory-feed.v0.json",
                  encoding="utf-8") as fh:
            polluted = json.load(fh)
        polluted["descriptionNote"] = "smuggled"
        with self.assertRaises(SchemaMismatch):
            validate_against_feed_schema(polluted, self.schema)

    def test_schema_rejects_public_directory_exposed(self):
        with open("contracts/examples/synthetic-observatory-feed.v0.json",
                  encoding="utf-8") as fh:
            exposed = json.load(fh)
        exposed["authorityFlags"]["publicDirectoryExposed"] = True
        with self.assertRaises(SchemaMismatch):
            validate_against_feed_schema(exposed, self.schema)

    def test_stored_example_equals_generated_exactly(self):
        with open("contracts/examples/synthetic-observatory-feed.v0.json",
                  encoding="utf-8") as fh:
            stored = json.load(fh)
        generated = contract_module.synthetic_dashboard_example()
        self.assertEqual(stored, generated)


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
        # R1: the ingestion seam is part of the contract and refuses by
        # default; component strings are explicitly not credentials.
        self.assertEqual(contract["ingestionSeam"]["defaultPolicy"], "refuse")
        self.assertFalse(contract["ingestionSeam"]["componentStringsAreCredentials"])
        self.assertTrue(contract["privacyContract"]["privateByDefault"])
        self.assertFalse(contract["authority"]["executionEligible"])
        blob = json.dumps(contract)
        self.assertNotIn(SECRET_TEXT, blob)

    def test_stable_item_order_is_truthful(self):
        # R1 finding 3: the contract must not advertise an ordering the
        # implementation does not perform.
        contract = contract_module.interface_contract()
        self.assertEqual(contract["feedContract"]["stableItemOrder"],
                         "recorderInsertionOrder")
        self.assertTrue(contract["feedContract"]["pageOffsetsStableUnderGrowth"])

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
        self.assertEqual(stored, generated)  # exact comparison (R1)

    def test_schema_file_pins_kind_and_false_flags(self):
        schema = load_feed_schema()
        self.assertEqual(schema["properties"]["kind"]["const"],
                         feed_module.DASHBOARD_KIND)
        self.assertEqual(schema["properties"]["authorityFlags"]["$ref"],
                         "#/$defs/authorityFlags")
        flags = schema["$defs"]["authorityFlags"]["properties"]
        self.assertEqual(set(flags), {
            "executionAuthorized", "publicationAuthorized",
            "deploymentAuthorized", "agentRegistrationActive",
            "publicDirectoryExposed"})
        self.assertTrue(all(props["const"] is False for props in flags.values()))
        self.assertEqual(
            set(schema["$defs"]["authorityFlags"]["required"]), set(flags))


if __name__ == "__main__":
    unittest.main()