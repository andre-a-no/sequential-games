# sequential-games

Mathematical and cybernetic models for participants pursuing their own goals
in asynchronous, stochastic environments. Participants can cooperate, compete
or have partially aligned interests. Deliberate waiting is an explicit decision.

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

## Repository status

This `main` branch is the repository entry point. The reference implementation
and its tests are currently in
[`feat/explicit-state-games-and-discovery`](https://github.com/andre-a-no/sequential-games/tree/feat/explicit-state-games-and-discovery).

That development branch contains an explicit-state, virtual-time simulator:
model and policy transitions, action admission and completion, waiting and
withdrawal, delayed private observations, independent random streams and
bounded continuation in memory. See its
[README](https://github.com/andre-a-no/sequential-games/blob/feat/explicit-state-games-and-discovery/README.md)
for the supported contracts, example and run commands.

The reference computation requires Python 3.11 or later and uses the standard
library at runtime. It does not provide an equilibrium solver, optimality or
fairness guarantees, a live executor, distributed semantics or validated disk
checkpoints. In-memory continuation does not establish durable recovery.

Earlier `sequential-search` ADRs excluded a separate games package. The current
division assigns independent participant objectives and coupled asynchronous
actions to `sequential-games`; a participant may still use `sequential-search`
within its own policy.
