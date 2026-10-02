"""The abort stack could not be imported: AbortDecision was imported by the manager, executor and
logger but never written; the logger imported two executor classes from the wrong module; the
manager's max() over a plain string Enum would have raised; and the integrations imported two
event helpers that did not exist. The call sites define the class."""
import asyncio

from src.resilience.abort.abort_manager import AbortManager
from src.resilience.events import create_integration_event, create_telemetry_event
from src.resilience.models.abort import (
    DEFAULT_FAILURE_RATE_POLICY, AbortAction, AbortDecision, AbortSeverity,
)


def test_severity_has_an_order():
    ranked = sorted(AbortSeverity, key=lambda s: s.rank)
    assert [s.value for s in ranked] == ["low", "medium", "high", "critical"]
    assert max([AbortSeverity.MEDIUM, AbortSeverity.CRITICAL, AbortSeverity.LOW], key=lambda s: s.rank) \
        is AbortSeverity.CRITICAL


def test_abort_decision_matches_how_the_manager_builds_it():
    d = AbortDecision(policy_id="p1", triggered=True, action=AbortAction.ROLLBACK,
                      severity=AbortSeverity.HIGH, reason="Manual abort: test", context={"k": 1})
    out = d.to_dict()
    assert out["policy_id"] == "p1" and out["triggered"] is True
    assert out["action"] == "rollback" and out["severity"] == "high" and out["context"] == {"k": 1}
    assert out["condition"] is None and out["metrics"] is None and out["decision_id"] and out["timestamp"]
    idle = AbortDecision(policy_id="p1", triggered=False)         # "no condition fired"
    assert idle.action is None and idle.severity is AbortSeverity.LOW and idle.to_dict()["action"] is None


def test_manager_triggers_the_default_policy_on_a_run_of_failures_and_not_on_success():
    async def go():
        healthy = AbortManager()
        for i in range(10):
            await healthy.record_operation(success=True, operation_id=f"ok{i}")
        assert (await healthy._evaluate_policy(DEFAULT_FAILURE_RATE_POLICY)).triggered is False
        failing = AbortManager()
        for i in range(10):
            await failing.record_operation(success=False, operation_id=f"bad{i}")
        d = await failing._evaluate_policy(DEFAULT_FAILURE_RATE_POLICY)
        assert d.triggered and d.action is AbortAction.SAVE_STATE_AND_STOP
        assert d.severity is AbortSeverity.HIGH                       # severity picked via the new ordering
    asyncio.run(go())


def test_integration_and_telemetry_events_carry_their_identifiers():
    e = create_integration_event("browser_integrated", {"resource_created": True},
                                 component="browser_lifecycle_integration", browser_id="b1")
    assert e.event_type == "integration_event" and e.component == "browser_lifecycle_integration"
    assert e.data == {"action": "browser_integrated", "browser_id": "b1", "resource_created": True}
    t = create_telemetry_event("metrics_collected", {"component_count": 4})
    assert t.event_type == "telemetry_event" and t.data["action"] == "metrics_collected" and t.component == "telemetry_integration"
