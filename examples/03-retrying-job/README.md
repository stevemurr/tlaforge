# Retrying Job

## Problem Statement

Model a job that can retry a bounded number of times before it fails permanently.

## State Model

- States: `queued`, `running`, `retry_wait`, `succeeded`, `failed`
- Initial state: `queued`
- Terminal states: `succeeded`, `failed`
- Auxiliary variable: `retries`
- Constant: `MaxRetries`

## Code Walk-Through

1. Add `retries` to `aux_vars`.
2. Initialize it with `aux_init={"retries": IntLit(0)}`.
3. Add `MaxRetries` as a TLA+ constant.
4. Add one helper definition, `CanRetry`, to name the retry-budget condition.
5. Add transitions that either preserve `retries` with `unchanged=["retries"]` or update it explicitly.
6. Add an invariant that keeps `retries` between `0` and `MaxRetries`.

The full builder code lives in [build.py](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/03-retrying-job/build.py).

## Run Command

Assuming you already created and activated a virtual environment, then ran `python -m pip install -e .` from the repo root:

```bash
python examples/03-retrying-job/build.py
```

The committed output is in [spec.tla](/Users/murr/Code/github.com/stevemurr/tlaforge/examples/03-retrying-job/spec.tla).

## What To Change Next

Try adding a second auxiliary variable such as `last_error`, then update the retry and failure transitions to keep it in sync.
