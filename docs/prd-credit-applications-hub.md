# Product Requirements Document: Credit Applications Hub (MVP)


## Overview

- **Product**: Credit Applications Hub
- **Repo**: `credit-applications-hub`
- **Status**: Draft
- **Last Updated**: 2026-02-14

## Problem

We need a base system to accept and process credit applications across multiple countries. Behavior varies by country (rules, provider integrations, and potentially status flows). The MVP must be extensible (add countries/providers/flows without large rewrites) and support asynchronous processing plus near real-time UI updates.

## Goals (MVP)

- Create, view, list (filterable), and update credit applications.
- Apply country-specific validation rules on create and/or status updates.
- Fetch and store country-specific provider/banking data (provider varies by country).
- Run at least one background workflow asynchronously and safely in parallel workers.
- Support one external integration flow (webhook in or webhook out).
- Surface relevant changes in near real-time in the frontend.

## Scope

### In scope

- Application lifecycle: create, read, list with filters, status transitions.
- Country rules via strategy/resolver pattern (no controller branching).
- Provider routing per country with adapters that can vary payload shape.
- Async jobs with idempotency and safe concurrency (at least one DB-driven enqueue flow).
- Basic caching for one read path.
- Basic auth (JWT or equivalent) and minimal authorization boundaries.
- Observability: structured logs + correlation across API, jobs, and webhook flow.
- Deployment artifacts: basic Kubernetes manifests for backend/frontend/workers (and db if included).

### Out of scope (MVP)

- Production-grade risk modeling/KYC/AML.
- Full country coverage on day one (MVP implements at least 2 end-to-end).

## Core Requirements

- **Application data**: country, applicant identity fields, requested amount, monthly income, application date, status, provider data reference/snapshot.
- **Validation**: per-country document checks plus at least one additional per-country rule (e.g., income vs amount, debt-to-income using provider data, or score/capacity-to-pay using provider data).
- **Listing**: filter at least by country; recommended additional filters: status, date range.
- **Status flow**: configurable per country; transitions can trigger side effects (notifications, re-evaluation, audit).
- **Async**: at least one DB change triggers enqueueing work processed by workers; workers can scale horizontally without obvious data races.
- **Webhooks**: at least one flow that sends or receives webhook data tied to the application model.
- **Realtime UI**: the UI reflects application/status changes within seconds via WebSocket/Socket.IO-style push.

## Phases

1. **Foundation**: data model + API endpoints + basic UI (create/list/detail/update-status).
2. **Multi-country**: add at least 2 countries with rule strategies and provider adapters.
3. **Async + integration + realtime**: DB-driven job enqueue, parallel workers, webhook flow, realtime UI updates.
4. **Hardening**: auth/authorization, caching, observability, scalability notes, k8s manifests.

## Acceptance Criteria (MVP)

- Two countries work end-to-end (create -> validate -> provider data -> async side effects -> view/list -> status updates).
- At least one async job runs via queue/jobs-table and updates application state or audit trail.
- A webhook flow is demonstrably integrated (send or receive) and results in an application update or recorded external event.
- Frontend updates near real-time via WebSocket/Socket.IO-style push when application status changes.


