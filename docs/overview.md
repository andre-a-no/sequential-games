# What sequential-games does

Languages: [English](overview.md) · [Русский](overview.ru.md)

`sequential-games` describes participants pursuing their own goals while their
actions jointly change a stochastic environment. It provides mathematical and
cybernetic contracts and a reproducible reference computation. Participants can
cooperate, compete, or have partially aligned interests.

The package belongs to the ecosystem's **methods layer**. Production runtimes,
message delivery infrastructure, durable storage and real tool execution belong
to engineering/application packages in `sequentialist-*`.

## Typical questions

- What should a participant do after a delayed observation?
- What happens if an intended action becomes invalid before it is admitted?
- Can one participant wait while others and the environment continue changing?
- Can a bounded simulation continue with an action still in flight?
- Which observations are available to each participant?

The current library supplies a framework for explicit models of those questions.
It does not automatically derive the best policy for an arbitrary game.

## Inputs and outputs

| Input | Meaning |
|---|---|
| Model | Pure transition functions for initialization, admission, completion and autonomous changes |
| World state | Explicit model state, not a hidden mutable model object |
| Policy and policy state for each participant | Decision function and that participant's own memory |
| Seed and time/event bounds | Reproducible random-stream allocation and computation limits |

`initialize(...)` returns a `SimulationState`. `run(...)` returns a `RunResult`
with updated state, processed-event count and an explicit stop reason:
`quiescent`, `time_limit` or `event_limit`. Quiescence means that no active event
remains; it does not prove that a participant achieved its goal or that no
solution exists. Goal satisfaction belongs to the supplied model/application.

Intentions distinguish `Action`, `Wait` and `Withdraw`. Busy participants are
tracked separately. An action is checked against model state at admission time;
the earlier intention is not itself a successful execution.

## A workflow for readers who do not code

Start with the [shared-resource example](../examples/shared_resource.py) and its
description in the [README](../README.md). A and B want their own jobs completed
on one machine. B first yields, later encounters contention, and waits for
availability. Durations are stochastic and notices are delayed.

Ask a developer or assistant to run that example with a named seed and explain
the returned trace: who chose to act or wait, what was rejected, when work
finished, and why processing stopped. Use separate seeds to explore alternative
modeled outcomes. Such a comparison is an experiment under this synthetic model,
not a guarantee about a real organization, market, robot or negotiation.

There is no ready-made web UI or live resource controller in this repository.
An engineering visualization adapter can render the privileged trace for
inspection; that trace must not be used as a participant's observation history.

## Information and timing boundaries

Policies receive their own state and observations already delivered to them.
Delayed notices retain the values captured at generation time. Policy-view event
identities are recipient-local; causal references to hidden/internal events are
removed. Full simulator traces remain privileged debugging data.

Events at equal model time follow explicit insertion order. This represents
asynchronous interleaving, not simultaneous joint-action resolution or fairness.
Autonomous timers can change the environment even if every participant waits.
An actor's pending action does not stop other actors, but its own next decision
waits for completion in the present implementation.

Model/policy callbacks are contractually pure and receive explicit random input.
The reference algorithm copies state at its public boundary; it cannot sandbox
arbitrary Python callbacks or prevent them from performing hidden I/O.

## Implemented scope and limits

The source implements explicit-state transitions, action admission/completion,
waiting and withdrawal, addressed observations, autonomous timers, overlapping
action durations, independent random streams, and bounded in-memory continuation.
The [tests](../tests/test_simulation.py) exercise these behaviors.

Not implemented in this slice:

- Simultaneous joint-action resolution, cancellation of accepted actions or
  interruption of the participant's pending action.
- Production scheduling, network workers, message brokers or external tools.
- Validated disk snapshots, durable restart or distributed execution semantics.
- Universal utility conversion, an equilibrium solver, regret bounds, optimal
  coordination or fairness guarantees.

`run` accepts unmodified states produced by `initialize` or a previous `run`.
This is not a general loader for arbitrary manually constructed snapshots.
Reproduction assumes the same supported Python PRNG implementation and compatible
model/policy versions. A seed does not reproduce unknown external services.

## Frequently asked questions

**Is waiting an action?** It is an explicit intention. The world can continue
changing while a participant waits; domain dynamics can assign delay or
opportunity costs. Busy/unavailable is a different condition.

**Is this a game-playing agent?** It supplies models and reference computation.
The caller supplies policies and objectives; an agentic package can implement a
participant using tools or LLMs without becoming mandatory for every model.

**Does it replace sequential-search?** No. Search can help a participant plan.
Games describes interaction with other participants and coupled world dynamics.

**Does it replace sequentialist-core?** No. Core supplies application engineering
such as durable execution and audit. Continuing a model state in memory is not
durable application recovery.

**Can I deploy it to control a shared resource?** The synthetic example is not a
live controller. Real execution needs an engineering adapter with explicit
delivery, authority, cancellation and recovery semantics.

## Sources and further reading

- [README and run commands](../README.md)
- [Contract definitions](../src/sequential_games/contracts.py)
- [Reference algorithm](../src/sequential_games/simulation.py)
- [Model/scheduling ADR](ADR-001-explicit-state-reference-simulation.md)
- [Shared-resource example](../examples/shared_resource.py)
- [Behavioral tests](../tests/test_simulation.py)
- [Developer navigation](../AGENTS.md) and [manifest](../pyproject.toml)

[llms.txt](../llms.txt) is a curated navigation index; no particular search
engine or assistant is guaranteed to read or index it.
