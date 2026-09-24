# Architecture documentation

Three documents, written together, each answering a different question. Open the
HTML files in a browser — they are self-contained apart from the shared
`_style.css` in this folder.

| # | Document | Answers | Open when |
|---|----------|---------|-----------|
| 1 | [System Architecture](01-system-architecture.html) | What is this, and how do the pieces fit? | You are new, or need the shape of the whole thing |
| 2 | [Package Reference](02-package-reference.html) | What is in every folder, and what may it import? | You are about to add or move code |
| 3 | [Language Boundaries](03-language-boundaries.html) | Why is this in Go and not Python? Where does my feature go? | You are deciding where something belongs |

```bash
xdg-open docs/architecture/01-system-architecture.html
```

## What each contains

**1 · System Architecture** — what the product is, the runtime topology, the
four-layer convention shared by all four services, a service inventory, the
request lifecycle hop by hop, the gRPC and OpenAPI contracts, the data model,
the configuration model, observability, the three deployment topologies,
failure modes, and a verified status report.

**2 · Package Reference** — every Go package, Python module, frontend folder and
CLI layer: purpose, contents, what it imports, who depends on it. Ends with the
import matrix and a "where does my new code go?" table.

**3 · Language Boundaries** — the concern map (24 concerns, who owns each), what
Go/Python/frontend/CLI each own and are forbidden, the three areas where the
same concern exists in two languages, a decision flowchart for new work, and an
honest accounting of what the polyglot split costs.

## Verification

Everything in these three was checked against the working tree on 2026-09-24 —
file paths, route tables, dependency lists, and the behavioural claims about
what is and is not wired. The repository has been restructured more than once,
so where an older document disagrees, it is the stale one.

Known stale: the root `ARCHITECTURE.md` predates the restructure and still
refers to `internal/middleware/` and `app/domain/`, neither of which exists.

## Related documents

| File | Covers |
|------|--------|
| `../BEGINNERS_GUIDE.md` | The concepts, explained without the code |
| `../annotated-codebase.html` | Every file dissected, concept taught inline |
| `../connection-atlas.html` | Every socket, and ten request flows traced hop by hop |
| `../gateway-teardown.html` | Architecture map plus an honest status report |
| `../BUILD_PUSH_DEPLOY.md` | Build → GitHub → Docker Hub → minikube runbook |
| `../deployment-deep-dive.html` | Docker and Kubernetes from zero |
| `../aws-deployment-guide.html` | Single-server EC2 deployment |

Note that `annotated-codebase.html` and `connection-atlas.html` were written
before the most recent restructure; their concepts hold but some file paths are
stale. Document 2 here supersedes their path references.
