# SPDX-License-Identifier: AGPL-3.0-only
"""A bounded virtual-time reference computation, not an operational runtime.

Public computations copy their input state. Models and policies receive explicit
state and random variates. Equal-time events execute in insertion order; this is
asynchronous interleaving, not simultaneous joint-action resolution.
"""
from __future__ import annotations

import copy
import heapq
import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from .contracts import Action, Choice, Effects, Event, Model, Policy, View, Wait, Withdraw


@dataclass(frozen=True, order=True)
class Scheduled:
    time: float
    order: int
    kind: str = field(compare=False)
    actor: str = field(default="", compare=False)
    data: dict[str, Any] = field(default_factory=dict, compare=False)
    cause: int | None = field(default=None, compare=False)
    generated_at: float = field(default=0.0, compare=False)


@dataclass(frozen=True)
class Participant:
    state: Any
    random_state: Any
    history: tuple[Event, ...] = ()
    waiting: Wait | None = None
    generation: int = 0
    busy: bool = False
    withdrawn: bool = False
    wake_pending: bool = False


@dataclass(frozen=True)
class SimulationState:
    world: Any
    participants: Mapping[str, Participant]
    random_state: Any
    now: float = 0.0
    pending: tuple[Scheduled, ...] = ()
    trace: tuple[Event, ...] = ()
    next_order: int = 0
    dispatch_delay: float = 0.0


@dataclass(frozen=True)
class RunResult:
    state: SimulationState
    reason: str  # quiescent, time_limit, event_limit
    processed: int


def _duration(value: float, name: str) -> None:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be finite and non-negative")


def _draw(state: Any) -> tuple[float, Any]:
    rng = random.Random()
    rng.setstate(state)
    return rng.random(), rng.getstate()


def initialize(model: Model, world: Any, policy_states: Mapping[str, Any], *,
               seed: int = 0, dispatch_delay: float = 0.0) -> SimulationState:
    """Create explicit initial state; no policy or environment RNG is shared.

    Actor insertion order determines initial equal-time decision priority.
    This priority is declared, not a fairness guarantee.
    """
    _duration(dispatch_delay, "dispatch_delay")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not policy_states or any(not isinstance(a, str) or not a for a in policy_states):
        raise ValueError("participants must have non-empty string identifiers")
    participants = {
        actor: Participant(copy.deepcopy(state), random.Random(f"{seed}:policy:{actor}").getstate())
        for actor, state in policy_states.items()
    }
    machine = _Machine(SimulationState(copy.deepcopy(world), participants,
                                      random.Random(f"{seed}:environment").getstate(),
                                      dispatch_delay=dispatch_delay))
    noise = machine.noise()
    transition = model.initialize(copy.deepcopy(machine.world), tuple(participants), 0.0, noise)
    machine.world = copy.deepcopy(transition.state)
    machine.effects(transition.effects, None)
    for actor in participants:
        machine.wake(actor, None)
    return machine.snapshot()


def run(model: Model, policies: Mapping[str, Policy], state: SimulationState, *,
        until: float | None = None, max_events: int = 10000) -> RunResult:
    """Return a new state and explicit stop reason; inputs remain unchanged.

    Each participant has at most one outstanding action. Observations delivered
    during that action accumulate; its policy resumes after completion. Live I/O,
    cancellation, simultaneous moves and durable storage are outside this API.
    state must be an unmodified result of initialize() or run(), not a manually
    assembled or deserialized snapshot. A snapshot-validation schema is future work.
    """
    _check_state_times(state)
    if set(policies) != set(state.participants):
        raise ValueError("policies must match the registered participants")
    if type(max_events) is not int or max_events < 0:
        raise ValueError("max_events must be a non-negative integer")
    if until is not None:
        _duration(until, "until")
        if until < state.now:
            raise ValueError("until cannot precede current model time")
    machine = _Machine(state)
    processed = 0
    reason = "quiescent"
    while machine.queue:
        if not machine.active(machine.queue[0]):
            heapq.heappop(machine.queue)
            continue
        if until is not None and machine.queue[0].time > until:
            machine.now = until
            reason = "time_limit"
            break
        if processed >= max_events:
            reason = "event_limit"
            break
        item = heapq.heappop(machine.queue)
        machine.now = item.time
        machine.process(model, policies, item)
        processed += 1
    return RunResult(machine.snapshot(), reason, processed)


def _check_state_times(state: SimulationState) -> None:
    _duration(state.now, "state.now")
    _duration(state.dispatch_delay, "state.dispatch_delay")
    for event in state.pending:
        _duration(event.time, "pending event time")
        if event.time < state.now:
            raise ValueError("pending events cannot precede current model time")


def _view(actor: str, now: float, history: tuple[Event, ...]) -> View:
    # Global trace positions would reveal events private to other participants.
    # Project identities and causal links into this recipient's information set.
    local_ids = {event.id: index for index, event in enumerate(history)}
    events = tuple(replace(event, id=index,
                           cause=None if event.cause is None else local_ids.get(event.cause))
                   for index, event in enumerate(history))
    return copy.deepcopy(View(actor, now, events))


class _Machine:
    """Local mutable implementation detail of the pure reference computation."""
    def __init__(self, state: SimulationState):
        state = copy.deepcopy(state)
        self.world = state.world
        self.actors = dict(state.participants)
        self.random_state = state.random_state
        self.now = state.now
        self.queue = list(state.pending)
        heapq.heapify(self.queue)
        self.trace = list(state.trace)
        self.order = state.next_order
        self.dispatch_delay = state.dispatch_delay

    def snapshot(self) -> SimulationState:
        return copy.deepcopy(SimulationState(self.world, self.actors, self.random_state, self.now,
                                             tuple(sorted(self.queue)), tuple(self.trace), self.order,
                                             self.dispatch_delay))

    def noise(self) -> float:
        noise, self.random_state = _draw(self.random_state)
        return noise

    def record(self, kind: str, actor: str = "", data: dict | None = None,
               cause: int | None = None, generated_at: float | None = None) -> Event:
        event = Event(len(self.trace), self.now, kind, actor, copy.deepcopy(data or {}), cause,
                      self.now if generated_at is None else generated_at)
        self.trace.append(event)
        return event

    def schedule(self, delay: float, kind: str, actor: str = "", data: dict | None = None,
                 cause: int | None = None, generated_at: float | None = None) -> None:
        _duration(delay, "event delay")
        when = self.now + delay
        _duration(when, "event time")
        heapq.heappush(self.queue, Scheduled(when, self.order, kind, actor, copy.deepcopy(data or {}),
                                           cause, self.now if generated_at is None else generated_at))
        self.order += 1

    def effects(self, effects: Effects, cause: int | None) -> None:
        for notice in effects.notices:
            if notice.recipient not in self.actors:
                raise ValueError(f"unknown notice recipient: {notice.recipient!r}")
            if not notice.kind:
                raise ValueError("notice kind must not be empty")
            self.schedule(notice.delay, "notice", notice.recipient,
                          {"kind": notice.kind, "payload": notice.data}, cause)
        for timer in effects.timers:
            self.schedule(timer.delay, "timer", data=timer.data, cause=cause)

    def wake(self, actor: str, cause: int | None) -> None:
        participant = self.actors[actor]
        if participant.withdrawn or participant.busy or participant.wake_pending:
            return
        self.actors[actor] = replace(participant, wake_pending=True)
        self.schedule(0.0, "decide", actor, cause=cause)

    def receipt(self, actor: str, kind: str, cause: int, data: dict | None = None) -> None:
        self.schedule(0.0, "notice", actor, {"kind": kind, "payload": data or {}}, cause)

    def active(self, item: Scheduled) -> bool:
        if item.kind != "deadline":
            return True
        participant = self.actors[item.actor]
        return participant.waiting is not None and participant.generation == item.data["generation"]

    def process(self, model: Model, policies: Mapping[str, Policy], item: Scheduled) -> None:
        actor = item.actor
        if item.kind == "notice":
            event = self.record(item.data["kind"], actor, item.data["payload"], item.cause,
                                item.generated_at)
            participant = self.actors[actor]
            self.actors[actor] = replace(participant, history=(*participant.history, event))
            waiting = participant.waiting
            if waiting is None or not waiting.kinds or event.kind in waiting.kinds:
                self.wake(actor, event.id)
        elif item.kind == "deadline":
            participant = self.actors[actor]
            if participant.waiting is not None and participant.generation == item.data["generation"]:
                event = self.record("wait.deadline", actor, cause=item.cause)
                self.actors[actor] = replace(participant, history=(*participant.history, event))
                self.wake(actor, event.id)
        elif item.kind == "decide":
            self.decide(policies[actor], actor, item.cause)
        elif item.kind == "begin":
            admission = model.begin(copy.deepcopy(self.world), actor,
                                    copy.deepcopy(item.data["action"]), self.now, self.noise())
            if type(admission.accepted) is not bool:
                raise ValueError("admission.accepted must be bool")
            _duration(admission.duration, "action duration")
            self.world = copy.deepcopy(admission.state)
            kind = "model.action.accepted" if admission.accepted else "model.action.rejected"
            event = self.record(kind, actor, {"reason": admission.reason}, item.cause)
            self.effects(admission.effects, event.id)
            if admission.accepted:
                self.receipt(actor, "action.accepted", event.id)
                self.schedule(admission.duration, "complete", actor, admission.token, event.id)
            else:
                self.actors[actor] = replace(self.actors[actor], busy=False)
                self.receipt(actor, "action.rejected", event.id, {"reason": admission.reason})
        elif item.kind == "complete":
            transition = model.complete(copy.deepcopy(self.world), actor, copy.deepcopy(item.data),
                                        self.now, self.noise())
            self.world = copy.deepcopy(transition.state)
            self.actors[actor] = replace(self.actors[actor], busy=False)
            event = self.record("model.action.completed", actor, cause=item.cause)
            self.effects(transition.effects, event.id)
            self.receipt(actor, "action.completed", event.id)
        elif item.kind == "timer":
            transition = model.on_timer(copy.deepcopy(self.world), copy.deepcopy(item.data),
                                        self.now, self.noise())
            self.world = copy.deepcopy(transition.state)
            event = self.record("environment.timer", data=item.data, cause=item.cause)
            self.effects(transition.effects, event.id)
        else:
            raise ValueError(f"unknown scheduled event: {item.kind!r}")

    def decide(self, policy: Policy, actor: str, cause: int | None) -> None:
        participant = self.actors[actor]
        noise, random_state = _draw(participant.random_state)
        choice = policy.decide(copy.deepcopy(participant.state),
                               _view(actor, self.now, participant.history), noise)
        if not isinstance(choice, Choice):
            raise TypeError("policy must return Choice")
        participant = replace(participant, state=copy.deepcopy(choice.state), random_state=random_state,
                              waiting=None, generation=participant.generation + 1, wake_pending=False)
        self.actors[actor] = participant
        intention = choice.intention
        if isinstance(intention, Action):
            if not isinstance(intention.kind, str) or not intention.kind:
                raise ValueError("action kind must be a non-empty string")
            event = self.record("intention.action", actor,
                                {"kind": intention.kind, "data": intention.data,
                                 "based_on": participant.history[-1].id if participant.history else None},
                                cause)
            self.actors[actor] = replace(participant, busy=True)
            self.schedule(self.dispatch_delay, "begin", actor, {"action": intention}, event.id)
        elif isinstance(intention, Wait):
            if intention.until is not None:
                _duration(intention.until, "wait deadline")
                if intention.until <= self.now:
                    raise ValueError("wait deadline must be strictly in the future")
            event = self.record("intention.wait", actor,
                                {"until": intention.until, "kinds": intention.kinds}, cause)
            self.actors[actor] = replace(participant, waiting=copy.deepcopy(intention))
            if intention.until is not None:
                self.schedule(intention.until - self.now, "deadline", actor,
                              {"generation": participant.generation}, event.id)
        elif isinstance(intention, Withdraw):
            self.record("intention.withdraw", actor, {"reason": intention.reason}, cause)
            self.actors[actor] = replace(participant, withdrawn=True)
        else:
            raise TypeError("intention must be Action, Wait or Withdraw")
