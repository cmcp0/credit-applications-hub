---
name: credit-app-mvp-guide
description: Implementation workflow for the credit-applications-hub MVP covering loan application creation/read/list/status updates, country-specific validation rules, provider routing by country, and asynchronous/parallel processing with near-real-time UI updates. Use when planning, implementing, or reviewing features in this repository.
---

# Credit Application MVP Guide

## Overview

Use this skill to keep implementation aligned with the eight MVP goals in `README.md`. Favor small vertical slices that deliver end-to-end behavior from API to background processing to UI updates.

## Delivery Workflow

### 1. Map the request to MVP goals

- Identify which goal numbers in `README.md` are affected.
- Define inputs, outputs, and state transitions before coding.
- Record explicit non-goals to keep scope tight.

### 2. Model the application lifecycle

- Treat a credit application as a single source of truth with a stable ID.
- Keep status transitions explicit (for example: `PENDING -> VALIDATED -> ROUTED -> APPROVED/REJECTED`).
- Reject invalid transitions in service/business layer, not only in controllers.

### 3. Isolate country rules

- Keep country validation in dedicated rule modules or strategy objects.
- Pass a normalized application object into the rule layer.
- Return structured validation errors (`field`, `code`, `message`) for API/UI use.

### 4. Isolate provider integrations

- Define a provider interface with methods for submit/query/update.
- Route by country through a resolver/factory instead of branching in controllers.
- Normalize provider responses into a shared internal shape.

### 5. Design async and parallel processing deliberately

- Put long-running business logic behind jobs/events.
- Make handlers idempotent so retries are safe.
- Store job/application correlation IDs to trace work across services.

### 6. Drive near-real-time UI updates

- Emit application status events when background work changes state.
- Prefer push channels (WebSocket/SSE) when available; otherwise poll with backoff.
- Keep payloads minimal and include timestamps/version markers to avoid stale updates.

### 7. Verify with scenario-based tests

- Add tests for:
  - Country rule acceptance/rejection paths.
  - Provider selection by country.
  - Status transition guards.
  - Async job processing and duplicate delivery.
- Include one end-to-end flow per supported country/provider path.

## Implementation Checklist

- MVP goal linkage is documented for each change.
- Validation and provider routing are decoupled from transport layer.
- Async handlers are retry-safe/idempotent.
- UI can observe status changes without manual refresh.
- Tests cover happy path and failure path for changed behavior.
