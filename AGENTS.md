# Repository guide

This package belongs to the mathematical/cybernetic `sequential-*` layer.
Keep model and policy state, model time and random inputs explicit. Production
workers, I/O, storage, brokers and tool dispatch belong to `sequentialist-*`.

## Read before changing contracts

- [README.md](README.md): actual supported API and limitations.
- [docs/overview.md](docs/overview.md): plain-language use cases and FAQ.
- [ADR-001](docs/ADR-001-explicit-state-reference-simulation.md): state, scheduling, privacy and continuation semantics.
- [contracts.py](src/sequential_games/contracts.py): model, policy, intention and event abstractions.
- [simulation.py](src/sequential_games/simulation.py): bounded reference algorithm and explicit state.
- [shared-resource example](examples/shared_resource.py): two separate participant goals.
- [tests](tests): observation privacy, waiting, input isolation and reproducibility.

Do not infer simultaneous-move, fairness, optimality, equilibrium, live execution
or durable-recovery guarantees from the reference example. Policy observations
must use the recipient-local projection, never the privileged global trace.
Maintain explicit stop reasons and preserve the current pure-state contract.

## Checks

Run from this repository root with Python 3.11+:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tests examples
mypy
python examples/shared_resource.py
```

Source dependencies and development tools are declared in
[pyproject.toml](pyproject.toml). Use the SPDX header style already present in
source files. Before documenting a capability as implemented, check its public
API and relevant tests; an ecosystem plan is not evidence of execution.
