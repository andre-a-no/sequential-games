# SPDX-License-Identifier: AGPL-3.0-only
"""Two jobs share a machine: each wants its own completion, B initially yields.

This is a synthetic model, not a production resource scheduler. No files,
threads or network calls are performed by its transitions or policies.
"""
from __future__ import annotations

from sequential_games import (
    Action,
    Admission,
    Choice,
    Effects,
    Notice,
    Transition,
    Wait,
    Withdraw,
    initialize,
    run,
)


class SharedResource:
    def initialize(self, state, actors, now, noise):
        return Transition(state, Effects(tuple(Notice(actor, "status", {"owner": state["owner"]})
                                               for actor in actors)))

    def begin(self, state, actor, action, now, noise):
        if action.kind != "work" or state["owner"] is not None:
            return Admission(state, False, reason="resource unavailable")
        world = {**state, "owner": actor}
        duration = 1.0 + noise  # explicit stochastic input; the model owns no RNG
        return Admission(world, True, duration, {"job": action.data["job"]})

    def complete(self, state, actor, token, now, noise):
        assert state["owner"] == actor
        world = {**state, "owner": None, "completed": (*state["completed"], token["job"])}
        return Transition(world, Effects(tuple(Notice(name, "available", {"owner": None}, delay=0.2)
                                                for name in ("A", "B"))))

    def on_timer(self, state, data, now, noise):
        return Transition(state)


class JobPolicy:
    def decide(self, state, view, noise):
        if any(event.kind == "action.completed" for event in view.events):
            return Choice(state, Withdraw("my task is complete"))
        if not state["yielded"] and state["yield_until"] > view.now:
            return Choice({**state, "yielded": True}, Wait(until=state["yield_until"]))
        rejection = next((event for event in reversed(view.events) if event.kind == "action.rejected"), None)
        available = next((event for event in reversed(view.events) if event.kind == "available"), None)
        if rejection is not None and (available is None or rejection.id > available.id):
            return Choice(state, Wait(kinds=("available",)))
        return Choice(state, Action("work", {"job": state["job"]}))


def experiment(seed=7):
    model = SharedResource()
    world = {"owner": None, "completed": ()}
    initial = initialize(model, world, {
        "A": {"job": "job-A", "yield_until": 0.0, "yielded": False},
        "B": {"job": "job-B", "yield_until": 0.5, "yielded": False},
    }, seed=seed, dispatch_delay=0.1)
    return run(model, {"A": JobPolicy(), "B": JobPolicy()}, initial)


if __name__ == "__main__":
    result = experiment()
    print("Completed:", result.state.world["completed"])
    print("Model time:", round(result.state.now, 3), "stop:", result.reason)
    for event in result.state.trace:
        if event.kind.startswith(("intention.", "model.action.")):
            print(round(event.time, 3), event.actor, event.kind, event.data)
