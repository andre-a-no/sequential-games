# ADR-001: Explicit-state stochastic interaction and reference simulation

Status: implemented first slice of ecosystem requirements G-01 through G-09.

## Boundary

`sequential-games` owns mathematical/cybernetic contracts and pure reference
computations. A production runtime, its communication protocols, tool adapters,
durable state and application orchestration belong to `sequentialist-*`.

The reference computation is a function of model, policies and explicit
`SimulationState`. It returns a new state and a stop reason. An ephemeral mutable
implementation is local to that computation; no model or participant state is
kept in a background loop or global variable.

## Pure contracts

`Model.initialize`, `begin`, `complete` and `on_timer` receive explicit world
state, model time and a uniform variate. They return a `Transition` or `Admission`
with new world state and `Effects`. Admission rechecks feasibility at its model
commit point. A rejected action has no completion; any state change or notices
on rejection must be returned explicitly by the model.

`Policy.decide(state, view, noise)` returns `Choice(new_state, intention)`.
`View` contains only actor identity, current model time and observations already
delivered to that actor. The world and other participants' histories are absent.
Each callback input is copied and returned values are detached. Arbitrary Python
callbacks remain responsible for avoiding I/O and hidden mutable state.

Intentions:

- `Action(kind, data)`: submit an action for admission after `dispatch_delay`.
- `Wait(until=None, kinds=())`: no intervention until a matching observation or
  deadline. Empty `kinds` matches any delivered observation. A deadline must be
  finite and strictly later than the current model time.
- `Withdraw(reason)`: stop making new decisions. Already accepted actions cannot
  be abandoned through this intention: a policy is invoked only when idle.

`Wait` is an explicit choice, distinct from an action still being processed.
It may incur time/opportunity costs through the domain's state dynamics and
objectives; there is no universal scalar utility or alpha-budget conversion.
A domain can represent a timed nonintervention as an `Action` whose model effects
leave the system uncontrolled. Waiting only controls when to reconsider.

## Events and causality

`Notice` is addressed to one recipient and captures its payload when generated.
Its delay affects delivery time, not the payload's observation time. Event fields
are `id`, `time` (delivery/model occurrence time), `generated_at`, `kind`, `actor`
(recipient or deciding actor), `data` and `cause` (prior event identity).
The full simulator trace and internal histories retain global IDs for privileged
audit. Before calling a policy, the reference computation renumbers its delivered
history from zero and maps causes only when the referenced event belongs to that
visible history; causes referring to hidden/internal events become null. This
prevents global-ID gaps and hidden causal references from leaking private events.
Policies receive only this recipient-local projection. A debugger must not feed that full trace to a policy.

`Timer` schedules an autonomous world transition. It can fire while everyone is
waiting or withdrawn. Timer chains are bounded by the caller's event/time limit.

Intention records include the most recent local observation identity as
`based_on`. Model admission/completion trace entries use `model.action.*`;
recipient-facing receipts use `action.*`. Those are distinct events linked by
causes. A domain can generate additional observations from admission/completion.

## Scheduling

Events are processed by increasing `(model_time, insertion_order)`. Initial
participant decisions follow the supplied mapping's insertion order. Generated
effects enter the queue before the decision wakeups they cause. This is an
explicit deterministic interleaving, not simultaneous-move game semantics, a
fairness guarantee or an optimal resource-allocation rule.

Each actor has at most one action in flight, including transmission delay.
Other actors continue. Observations received while busy accumulate, but that
actor's next decision waits for completion. There is no cancellation or action
interruption in this slice. `Wait` is interrupted only by a matching observation
or its deadline. Obsolete deadline entries are discarded without advancing time.

## Random inputs and reproducibility

Environment and participant random states are explicit fields. Initialization
allocates independent PRNG streams using the seed and stable actor identifiers;
adding an actor does not perturb another actor's stream. Before each model or
policy invocation, the reference algorithm draws one uniform variate and returns
the updated corresponding PRNG state. Callbacks receive only the variate, never
a mutable RNG or its hidden state.

One variate per invocation is intentionally limited. More complex distributions
or correlated stochastic inputs need a declared model/input design; callbacks
must not silently call a second global RNG. Reproduction is promised for the
same supported Python PRNG implementation and model/policy versions, not across
arbitrary languages or unknown external services.

## Bounds and continuation

`run` returns `quiescent`, `time_limit` or `event_limit`. No-solution, domain
failure or game success is not inferred from queue exhaustion. Participant goals
and rewards remain the application's model responsibility.

`until` is an upper processing-time bound, not a mandatory duration. If no event
can occur before it, processing returns at that bound; if no event remains at all,
the computation is quiescent at its last event time. Event limits stop at an
explicit boundary and preserve pending work. Continuing returned state with the
same callbacks reproduces the uninterrupted suffix, including actions in flight.

`run` accepts only unmodified states produced by `initialize` or a prior `run`.
Finite/monotone time checks catch malformed temporal state, but there is no
general validation or restoration schema for arbitrary constructed/deserialized
state. There is no disk codec, persistent scheduler, external-effect recovery,
cryptographic audit or schema migration in this slice.

## Acceptance evidence

Tests cover reproducible shared-resource jobs with partially aligned goals,
explicit waiting/yielding, overlap of independent actions, equal-time ordering,
stale-intention rejection, autonomous environment transitions, observation
isolation and generation-time payloads, independent policy random streams,
non-finite delay rejection and continuation with an unfinished action.
