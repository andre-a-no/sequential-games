# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import copy
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from sequential_games import (
    Action,
    Admission,
    Choice,
    Effects,
    Notice,
    Timer,
    Transition,
    Wait,
    Withdraw,
    initialize,
    run,
)


class PassiveModel:
    def initialize(self, state, actors, now, noise):
        return Transition(state)

    def begin(self, state, actor, action, now, noise):
        return Admission(state, True, 1.0)

    def complete(self, state, actor, token, now, noise):
        return Transition(state)

    def on_timer(self, state, data, now, noise):
        return Transition(state)


class Waiting:
    def decide(self, state, view, noise):
        return Choice(state, Wait())


class Once:
    def decide(self, state, view, noise):
        if state:
            return Choice(state, Withdraw())
        return Choice(True, Action("work", {"job": view.actor}))


def load_example():
    path = Path(__file__).resolve().parents[1] / "examples" / "shared_resource.py"
    spec = importlib.util.spec_from_file_location("shared_resource", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resource_example_reproducibility_and_independent_goals():
    example = load_example()
    result = example.experiment()
    assert result == example.experiment()
    assert result.reason == "quiescent"
    assert result.state.world["completed"] == ("job-A", "job-B")
    assert all(actor.withdrawn for actor in result.state.participants.values())
    waits = [event for event in result.state.trace if event.kind == "intention.wait"]
    assert any(event.actor == "B" and event.data["until"] == 0.5 for event in waits)
    assert any(event.kind == "model.action.rejected" for event in result.state.trace)
    assert result != example.experiment(seed=8)


def test_pure_computation_keeps_inputs_and_can_resume_work_in_flight():
    example = load_example()
    model = example.SharedResource()
    world = {"owner": None, "completed": ()}
    policies = {"A": Once(), "B": Waiting()}
    initial = initialize(model, world, {"A": False, "B": None}, seed=3)
    saved = copy.deepcopy(initial)
    prefix = run(model, policies, initial, until=0.5)
    assert prefix.reason == "time_limit"
    assert prefix.state.participants["A"].busy
    resumed = run(model, policies, prefix.state)
    uninterrupted = run(model, policies, initial)
    assert resumed.state == uninterrupted.state
    assert initial == saved
    assert world == {"owner": None, "completed": ()}


def test_actions_overlap_in_model_time_and_equal_time_order_is_explicit():
    model = PassiveModel()
    initial = initialize(model, None, {"A": False, "B": False})
    result = run(model, {"A": Once(), "B": Once()}, initial)
    admitted = [e for e in result.state.trace if e.kind == "model.action.accepted"]
    completed = [e for e in result.state.trace if e.kind == "model.action.completed"]
    assert [(e.actor, e.time) for e in admitted] == [("A", 0.0), ("B", 0.0)]
    assert [(e.actor, e.time) for e in completed] == [("A", 1.0), ("B", 1.0)]
    assert all(e.cause is None or e.cause < e.id for e in result.state.trace)


def test_autonomous_environment_continues_when_everyone_waits():
    class Weather(PassiveModel):
        def initialize(self, state, actors, now, noise):
            return Transition(state, Effects(timers=(Timer(2.0),)))

        def on_timer(self, state, data, now, noise):
            return Transition(state + 1, Effects(notices=(Notice("A", "weather", {"value": state + 1}),)))

    class Observer:
        def decide(self, state, view, noise):
            return Choice(state, Withdraw() if view.events else Wait(kinds=("weather",)))

    initial = initialize(Weather(), 0, {"A": None, "B": None})
    result = run(Weather(), {"A": Observer(), "B": Waiting()}, initial)
    assert result.state.world == 1 and result.state.now == 2.0
    assert result.state.participants["A"].withdrawn
    assert result.state.participants["B"].history == ()


def test_delayed_observation_captures_generation_time_not_future_world():
    class Changing(PassiveModel):
        def initialize(self, state, actors, now, noise):
            return Transition(state, Effects((Notice("A", "sample", {"value": state}, delay=3),),
                                             (Timer(1),)))

        def on_timer(self, state, data, now, noise):
            return Transition(99)

    initial = initialize(Changing(), 1, {"A": None, "B": None})
    result = run(Changing(), {"A": Waiting(), "B": Waiting()}, initial)
    event, = result.state.participants["A"].history
    assert (event.data, event.generated_at, event.time) == ({"value": 1}, 0.0, 3.0)
    assert result.state.world == 99
    assert result.state.participants["B"].history == ()


def test_stale_intention_is_rejected_against_state_at_admission():
    class Closing(PassiveModel):
        def initialize(self, state, actors, now, noise):
            return Transition(state, Effects(timers=(Timer(0.5),)))

        def on_timer(self, state, data, now, noise):
            return Transition(False)

        def begin(self, state, actor, action, now, noise):
            return Admission(state, state, reason="closed" if not state else "")

    initial = initialize(Closing(), True, {"A": False}, dispatch_delay=1)
    result = run(Closing(), {"A": Once()}, initial)
    assert any(event.kind == "model.action.rejected" and event.time == 1 for event in result.state.trace)
    assert not any(event.kind == "model.action.completed" for event in result.state.trace)


def test_policy_cannot_mutate_world_or_another_participants_observations():
    class Source(PassiveModel):
        def initialize(self, state, actors, now, noise):
            data = {"values": [1]}
            return Transition(state, Effects((Notice("A", "sample", data), Notice("B", "sample", data))))

    class Mutating:
        def decide(self, state, view, noise):
            view.events[0].data["values"].append(999)
            state.append(999)
            return Choice(state, Withdraw())

    policy_states = {"A": [], "B": []}
    initial = initialize(Source(), {"hidden": 17}, policy_states)
    result = run(Source(), {"A": Mutating(), "B": Waiting()}, initial)
    assert initial.participants["A"].state == []
    assert policy_states == {"A": [], "B": []}
    assert result.state.participants["A"].history[0].data == {"values": [1]}
    assert result.state.participants["B"].history[0].data == {"values": [1]}
    assert result.state.world == {"hidden": 17}


def test_stale_wait_deadline_does_not_advance_time_after_early_wakeup():
    class Early(PassiveModel):
        def initialize(self, state, actors, now, noise):
            return Transition(state, Effects((Notice("A", "wake", delay=1),)))

    class Until:
        def decide(self, state, view, noise):
            return Choice(state, Withdraw() if view.events else Wait(until=100))

    result = run(Early(), {"A": Until()}, initialize(Early(), None, {"A": None}))
    assert result.reason == "quiescent"
    assert result.state.now == 1


def test_event_limit_and_time_limit_are_explicit_and_resumable():
    initial = initialize(PassiveModel(), None, {"A": False})
    limited = run(PassiveModel(), {"A": Once()}, initial, max_events=1)
    assert limited.reason == "event_limit" and limited.processed == 1
    assert run(PassiveModel(), {"A": Once()}, limited.state).state == run(
        PassiveModel(), {"A": Once()}, initial).state
    assert run(PassiveModel(), {"A": Once()}, initial, max_events=0).state == initial


def test_policy_random_stream_is_independent_of_other_participant_presence():
    class RandomPolicy:
        def decide(self, state, view, noise):
            return Choice(noise, Withdraw())

    model = PassiveModel()
    one = run(model, {"A": RandomPolicy()}, initialize(model, None, {"A": None}, seed=19))
    two = run(model, {"A": RandomPolicy(), "B": RandomPolicy()},
              initialize(model, None, {"A": None, "B": None}, seed=19))
    assert one.state.participants["A"].state == two.state.participants["A"].state


@pytest.mark.parametrize("deadline", [0, -1, float("inf"), float("nan"), True])
def test_invalid_wait_deadlines_fail_instead_of_busy_looping(deadline):
    class Invalid:
        def decide(self, state, view, noise):
            return Choice(state, Wait(until=deadline))

    model = PassiveModel()
    initial = initialize(model, None, {"A": None})
    with pytest.raises(ValueError):
        run(model, {"A": Invalid()}, initial)


@pytest.mark.parametrize("delay", [-1, float("inf"), float("nan"), True])
def test_invalid_dispatch_delays_are_rejected(delay):
    with pytest.raises(ValueError):
        initialize(PassiveModel(), None, {"A": None}, dispatch_delay=delay)


def test_unknown_recipient_and_missing_policy_are_rejected():
    class Invalid(PassiveModel):
        def initialize(self, state, actors, now, noise):
            return Transition(state, Effects((Notice("missing", "secret"),)))

    with pytest.raises(ValueError, match="recipient"):
        initialize(Invalid(), None, {"A": None})
    with pytest.raises(ValueError, match="policies"):
        run(PassiveModel(), {}, initialize(PassiveModel(), None, {"A": None}))


def test_private_event_metadata_does_not_leak_through_global_ids_or_causes():
    class Secret(PassiveModel):
        def initialize(self, state, actors, now, noise):
            private = (Notice("B", "private", {"secret": True}),) if state else ()
            return Transition(state, Effects((*private, Notice("A", "public", {"value": 1}))))

    class Capture:
        def decide(self, state, view, noise):
            return Choice(view, Withdraw())

    def observed(secret):
        result = run(Secret(), {"A": Capture(), "B": Waiting()},
                     initialize(Secret(), secret, {"A": None, "B": None}))
        return result.state.participants["A"].state, result.state

    without, plain_state = observed(False)
    with_hidden, hidden_state = observed(True)
    assert with_hidden == without
    assert [event.id for event in with_hidden.events] == [0]
    # Internal histories retain privileged global identity for audit/based_on.
    assert plain_state.participants["A"].history[0].id == 0
    assert hidden_state.participants["A"].history[0].id == 1


def test_policy_view_causal_links_only_reference_local_visible_events():
    from sequential_games import Event
    from sequential_games.simulation import _view

    view = _view("A", 5, (Event(10, 1, "first", "A"),
                           Event(20, 2, "second", "A", cause=10),
                           Event(30, 3, "third", "A", cause=11)))
    assert [(event.id, event.cause) for event in view.events] == [(0, None), (1, 0), (2, None)]


@pytest.mark.parametrize("now", [-1, float("inf"), float("nan"), True])
def test_invalid_state_time_is_rejected(now):
    initial = initialize(PassiveModel(), None, {"A": None})
    with pytest.raises(ValueError, match="state.now"):
        run(PassiveModel(), {"A": Waiting()}, replace(initial, now=now))


def test_pending_event_before_current_time_is_rejected():
    initial = initialize(PassiveModel(), None, {"A": None})
    with pytest.raises(ValueError, match="precede"):
        run(PassiveModel(), {"A": Waiting()}, replace(initial, now=1))
