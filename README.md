# sequential-games

Mathematical and cybernetic models, algorithms and algorithmic abstractions for
participants pursuing their own objectives in asynchronous, stochastic
environments. Participants can cooperate, compete or have partially aligned
interests. Deliberate waiting is an explicit decision.

Python 3.11+, standard-library runtime only. License: AGPL-3.0-only.

## Conceptual framework: the Sequentialist ecosystem

The ecosystem studies sequential decisions: observations arrive, evidence
changes, and a policy chooses whether to continue, act, wait or stop. It separates
three questions within the mathematical and cybernetic methods layer:

| Library | Central question | Responsibility |
|---|---|---|
| [sequential-analysis](https://github.com/andre-a-no/sequential-analysis) | What can we infer from the observations available so far? | Statistical tests, estimation, filtering, prediction and procedure-specific uncertainty guarantees. |
| [sequential-search](https://github.com/andre-a-no/sequential-search) | Which step should we explore next to reach an answer or a goal? | Search and reasoning over alternatives, experiments and rules, with explicit evidence, provenance and resource costs. |
| [sequential-games](https://github.com/andre-a-no/sequential-games) | How do participants pursue their own goals while their actions change a shared environment? | Interaction models for cooperation, competition and partially aligned interests, including asynchronous actions, local information and deliberate waiting. |

These are complementary responsibilities. A participant's policy can use search
to plan and statistical analysis to interpret observations; other participants
continue to act according to their own objectives. This describes how the
methods can be composed. Each package's implementation status is stated
separately below.

The naming convention expresses a further separation into three layers:

| Layer | Packages | Responsibility |
|---|---|---|
| Mathematical and cybernetic methods | `sequential-*`: analysis, search, games | Models, algorithms, explicit state and the assumptions under which a result holds. |
| Reusable engineering platform | `sequentialist-*`, including [core](https://github.com/andre-a-no/sequentialist-core) and [visuals](https://github.com/andre-a-no/sequentialist-visuals) | Durable application execution, storage, recovery, audit and presentation, according to each package's implemented scope. |
| Domain applications | `sequentialist-*`, including [ab](https://github.com/andre-a-no/sequentialist-ab), [quality](https://github.com/andre-a-no/sequentialist-quality), [monitor](https://github.com/andre-a-no/sequentialist-monitor), [clinical](https://github.com/andre-a-no/sequentialist-clinical) and [agentic](https://github.com/andre-a-no/sequentialist-agentic) | Subject-specific goals, workflows, adapters and user-facing decisions built from the methods and engineering components they need. |

Both the engineering platform and applications use the `sequentialist-*`
prefix. The platform is an open family of reusable packages; `core` currently
provides durable tasks built around `sequential-analysis` runs. This organization
does not imply that every combination already has an integration.

Across the ecosystem, state, information available to a decision, randomness,
costs and stopping reasons should be explicit. Evidence, resource expenditure
and real-world effects have separate meanings. Statistical validity, derivability
under supplied rules, properties of an interaction model and reliable execution
each require their own justification; a guarantee in one layer does not
automatically establish a guarantee in another.

## First executable slice

The package provides an explicit-state, virtual-time reference computation:

- Pure model transitions receive world state, actor/action, model time and one
  explicit uniform random input; they return new state and effects.
- Pure policies receive their own state, delivered observation history and a
  separate random input. They return updated policy state and an intention.
- `Action`, `Wait` and `Withdraw` distinguish intervention, deliberate inactivity
  and departure. Busy/unavailable participants are tracked separately.
- Effects can schedule observations and autonomous environment transitions.
  The environment continues even while every participant waits.
- Pending action durations overlap in model time. Preconditions are checked when
  an intention reaches admission, so a formerly valid decision can be rejected.
- Observations carry generation and delivery times; delayed data never becomes
  a new view of the later world. Private observations are never passed to other
  policies. Policy-view identities are recipient-local; causal links to hidden
  events are removed so metadata cannot reveal another actor's private events.
- Algorithm state includes pending events, local histories, policy state and
  independent environment/participant PRNG states. Continuing a bounded run
  preserves the trace of the uninterrupted computation.

This is a reference algorithm, not a service runtime. Real clocks, workers,
message brokers, storage, tool dispatch and retries belong to engineering
packages in `sequentialist-*`.

## Try the shared-resource example

```bash
python -m pip install -e '.[dev]'
python examples/shared_resource.py
python -m pytest -q
```

Two participants want their own jobs completed on one shared machine. B initially
waits to yield priority to A, later encounters an occupied resource, and waits
for its release. Job duration is stochastic and availability notices are delayed.
The model logs action rejection and completion separately, and both participants
withdraw after their own completion. This demonstrates partially aligned goals;
it is not a claim of optimal coordination or fairness.

For a caller-supplied model and policies:

```python
from sequential_games import initialize, run

# model contains transition functions, not hidden world state.
# policies map actor identifiers to policies with no hidden participant state.
state = initialize(model, world, policy_states, seed=7, dispatch_delay=0.1)
prefix = run(model, policies, state, until=2.0, max_events=1000)
result = run(model, policies, prefix.state, max_events=1000)
print(result.reason)  # quiescent, time_limit or event_limit
```

Public `initialize` and `run` copy state at their boundaries. `run` accepts only
unmodified states returned by these functions; manually assembled or deserialized
states have no validated snapshot contract yet. Basic finite/monotone-time checks
reject invalid time state. Callbacks are
contractually pure: no I/O, wall-clock reads or hidden mutation. The implementation
passes isolated input copies, but cannot prevent a supplied Python callback from
performing external side effects. It does not inspect callback code.

## Model and scheduling semantics

See [ADR-001](docs/ADR-001-explicit-state-reference-simulation.md) for the contract,
ordering rules, random-input allocation and supported limits.

Earlier sequential-search ADRs excluded a separate games package. This package
covers independent participant objectives and coupled asynchronous actions,
rather than treating another participant only as an observation source.

Not implemented: simultaneous joint-action resolution, cancellation of accepted
actions, interruption of a participant's pending action, live executors,
distributed semantics or disk checkpoint codecs. State can be continued in memory;
this does not establish durable recovery. No equilibrium, regret, safety or
optimality guarantee is implied by the contracts or example.

## Reading and repository navigation

Start with the [plain-language overview](docs/overview.md) for use cases, inputs,
outputs and FAQ. [llms.txt](llms.txt) indexes documentation and source evidence;
[AGENTS.md](AGENTS.md) maps developer entry points and checks.
