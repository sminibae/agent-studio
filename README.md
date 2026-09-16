# Agent Studio

Agent Studio is a developer workspace for configuring, running, evaluating, and
comparing agents. The current implementation establishes the first vertical slice:
Next.js → FastAPI → PostgreSQL, with an immutable identity boundary ready for
owner-scoped product data.

## Prerequisites

- Node.js 24.21.0 and pnpm 10.33.0
- Python 3.13.15 and uv 0.12.14
- Docker Desktop with Compose
- GNU Make

`uv` installs the pinned Python runtime automatically. Docker Desktop must be
running before database, integration, or E2E commands.

## Start locally

```sh
make install
make dev
```

The web app is available at <http://localhost:3000>. The API documentation is at
<http://localhost:8000/api/docs>. `make dev` starts PostgreSQL, applies migrations,
and runs the API and web development servers. Use `make db-down` to stop the
database container without deleting its volume.

Development mode ignores incoming identity headers and provisions the fixed local
developer from application settings. Production requires a trusted proxy credential
and an allowlisted `(issuer, subject)` pair; see `.env.example` for variable names.

## Verify

```sh
make check
make test-integration
make test-e2e
```

`make check` performs non-mutating formatting/lint checks, strict type checks,
unit/component tests, OpenAPI generation drift checks, and a production frontend
build. Integration tests use the PostgreSQL 18 container. The E2E smoke starts both
applications and verifies readiness and the current user through the Next.js proxy.

The product and engineering contracts are documented in [`docs/`](docs/README.md),
and implementation slices are tracked in [`plan/`](plan/00_start.md).
