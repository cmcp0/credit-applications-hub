---
name: bounded-context-implementation-guide
description: Implement or refactor repository code to match the bounded-context architecture defined in `docs/bounded-context-structure.md`. Use when creating a new bounded context under `src/`, adding modules by business capability, enforcing domain/application/infrastructure boundaries, or aligning shared code placement between `src/shared` and `src/{context_name}/shared`.
---

# Bounded Context Implementation Guide

## Overview

Implement code changes that conform to the bounded-context template in `docs/bounded-context-structure.md`. Prefer deterministic scaffolding first, then fill business behavior.

## Inputs

- `context_name`: bounded context folder name under `src/` (example: `applications`)
- `modules`: business-capability module names (example: `intake validation routing`)
- `module_responsibilities`: one sentence per module describing the business scope
- `features`: concrete use cases to implement per module

## Workflow

### 1. Read the architecture source of truth

- Read `docs/bounded-context-structure.md` before editing code.
- Preserve these rules:
  - Keep bounded contexts directly under `src/`.
  - Keep module internals split into `domain/`, `application/`, and `infrastructure/`.
  - Keep app/framework entrypoints out of `src/`.

### 2. Map requirements to modules

- Define module boundaries by business capability, not by technical concern.
- Assign each feature to exactly one owning module.
- Define integration points as domain events first; use direct orchestration only when explicit coordination is required.

### 3. Scaffold structure deterministically

- Run `scripts/scaffold_bounded_context.py` to create baseline folders and files:

```bash
python3 .agents/skills/bounded-context-implementation-guide/scripts/scaffold_bounded_context.py \
  --context applications \
  --modules intake validation routing
```

- Use `--dry-run` to preview filesystem changes.
- Use `--force` only when intentional overwrites are required.

### 4. Implement module internals

- Implement entities, value objects, domain events, and domain ports in `domain/`.
- Implement commands/queries/services and application ports in `application/`.
- Implement repositories, adapters, and subscribers in `infrastructure/`.
- Keep business rules out of infrastructure and app entrypoints.

### 5. Place shared code correctly

- Put cross-context reuse in `src/shared/`.
- Put context-local reuse in `src/<context_name>/shared/`.
- Keep module-specific code inside the owning module.

### 6. Validate architecture boundaries

- Verify each module still has one clear responsibility (SRP).
- Verify dependencies point toward abstractions/ports (DIP).
- Verify new capabilities are additive without invasive rewrites (OCP).
- Verify module communication uses events/contracts and avoids hard coupling.

## Script Reference

`scripts/scaffold_bounded_context.py` creates this baseline per module:

- `domain/entities.py`
- `domain/events.py`
- `domain/value_objects.py`
- `domain/ports/__init__.py`
- `application/ports/__init__.py`
- `application/services/__init__.py`
- `infrastructure/adapters/__init__.py`
- `infrastructure/subscribers/__init__.py`

It also creates:

- `src/<context_name>/shared/{domain,application,infrastructure}/__init__.py`
- `src/<context_name>/persistence/models.py`

## Output Contract

- Produce code changes that match the bounded-context template exactly.
- Include a short summary of:
  - modules created/updated
  - domain events used for module communication
  - any code moved to `src/shared/` or `src/<context_name>/shared/`
