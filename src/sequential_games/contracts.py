# SPDX-License-Identifier: AGPL-3.0-only
"""Mathematical contracts: model and policy state and random inputs are explicit."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Event:
    """An occurrence; policy views use recipient-local IDs and visible-only causes.

    The privileged simulator trace/internal histories retain global identities.
    """
    id: int
    time: float
    kind: str
    actor: str
    data: dict[str, Any] = field(default_factory=dict)
    cause: int | None = None
    generated_at: float = 0.0


@dataclass(frozen=True)
class View:
    actor: str
    now: float
    events: tuple[Event, ...]


@dataclass(frozen=True)
class Action:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Wait:
    """Reconsider on matching observations or at a deadline; the world continues.

    Empty kinds matches any observation; until=None adds no deadline.
    """
    until: float | None = None
    kinds: tuple[str, ...] = ()


@dataclass(frozen=True)
class Withdraw:
    reason: str = ""


@dataclass(frozen=True)
class Notice:
    recipient: str
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0


@dataclass(frozen=True)
class Timer:
    """An autonomous future model transition, including while everyone waits."""
    delay: float
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Effects:
    notices: tuple[Notice, ...] = ()
    timers: tuple[Timer, ...] = ()


@dataclass(frozen=True)
class Transition:
    state: Any
    effects: Effects = Effects()


@dataclass(frozen=True)
class Admission:
    """Action feasibility at admission time, not at the earlier decision time."""
    state: Any
    accepted: bool
    duration: float = 0.0
    token: dict[str, Any] = field(default_factory=dict)
    effects: Effects = Effects()
    reason: str = ""


@dataclass(frozen=True)
class Choice:
    state: Any
    intention: Action | Wait | Withdraw


class Policy(Protocol):
    def decide(self, state: Any, view: View, noise: float) -> Choice:
        """Pure decision with explicit policy state and uniform random input."""
        ...


class Model(Protocol):
    """Pure model transitions; no wall clock, I/O or private mutable model state.

    noise is one explicit uniform variate in [0,1). Model state belongs entirely
    in state. Returned values must describe the new state and generated effects.
    """
    def initialize(self, state: Any, actors: tuple[str, ...], now: float, noise: float) -> Transition: ...

    def begin(self, state: Any, actor: str, action: Action, now: float, noise: float) -> Admission: ...

    def complete(self, state: Any, actor: str, token: dict[str, Any], now: float,
                 noise: float) -> Transition: ...

    def on_timer(self, state: Any, data: dict[str, Any], now: float, noise: float) -> Transition: ...
