# Build → GitHub → Docker Hub → Minikube

A runbook. Every command here was executed against this repo before it was
written, except where a step is marked **untested** (those need credentials or
tools not present on this machine).

---

## 0. What was already broken, and what is now fixed

Five things blocked the build. All five are fixed in your working tree — this
section is so you know what changed and why, not something you need to do.

| # | Problem | Fix applied |
|---|---|---|
| 1 | `backend-python` had no `.dockerignore`, so `docker build` sent a **7.4 GB** context (the local `.venv`) and baked it into the image | Added `backend-python/.dockerignore`. Context is now 2.4 MB. |
| 2 | `sentence-transformers` was a hard dependency, pulling torch + CUDA. Image was **8.93 GB**. Nothing under `app/` imports it. | Moved to an optional `[ml]` extra in `pyproject.toml`. Image is now **720 MB**. |
| 3 | `instrumentation.ts` used `(0, eval)('import(...)')`. Turbopack bans dynamic code evaluation in the Edge runtime, so `pnpm build` failed. | Replaced with a normal dynamic `import()`. The existing runtime guard already prevents it loading on Edge. |
| 4 | 16 TypeScript errors failed the Next.js production build | All 16 fixed. `tsc --noEmit` is clean. Includes two real runtime bugs: server actions read `session.accessToken` (the callback stores `backendJwt`) and posted to `/keys` where the route is `/v1/keys`. |
| 5 | `frontend-web/Dockerfile` copies `/app/public`, which did not exist | Created `frontend-web/public/.gitkeep`. |

Also added: `gateway-go/.dockerignore`, and a new
`infrastructure/kubernetes/overlays/minikube/` (see §5).

Verified image sizes:

```
openrouter/gateway-go:dev        26.5 MB
openrouter/backend-python:dev     720 MB
openrouter/frontend-web:dev       280 MB
```

---

## 1. Prerequisites

Present on this machine: `docker`, `go`, `node` (v24 via nvm), `git`.
**Missing:** `minikube`, `kubectl`, `kustomize`, `pnpm`.

```bash
# kubectl
curl -fsSLO "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl
kubectl version --client

# minikube
curl -fsSLO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
minikube version

# kustomize (kubectl has one built in, but it lags; the standalone is safer)
curl -fsSL "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
sudo mv kustomize /usr/local/bin/

# pnpm — only needed to run the frontend outside Docker
corepack enable && corepack prepare pnpm@9.15.0 --activate
```

> You do **not** need pnpm, Go, or Python locally to build the images — every
> Dockerfile is multi-stage and self-contained. They are only needed to run
> tests and dev servers on the host.

---

## 2. Build all services

### 2.1 Generate the gRPC stubs first

Generated protobuf code is **gitignored** (`gateway-go/internal/repository/proto/`,
`backend-python/app/repository/grpc/gen/`). It exists in your tree now, but a
fresh clone will not have it and the Go build will fail without it.

```bash
cd ~/Documents/practice/prac1/git.normal/openrouter

# One-time: the protoc plugins
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

make proto          # writes stubs for both Go and Python
```

If `make proto` complains about `grpc_tools`, it is using the Python venv —
see the note in §7 about the broken venv.

### 2.2 Run the tests

```bash
# Go — note CGO_ENABLED=0; this box lacks the libc headers cgo wants
CGO_ENABLED=0 go test ./... -C gateway-go

# Frontend typecheck (in a container, so no local pnpm needed)
cd frontend-web
docker run --rm -v "$PWD":/app -w /app node:20-alpine \
  sh -c './node_modules/.bin/tsc --noEmit'
cd ..
```

Expected: Go is green except `TestLimiter_ResetAtIsInTheFuture`, which fails
because miniredis's embedded Lua clamps a 64-bit millisecond timestamp to
int32. It is a test-harness limitation, not a production bug — real Redis
returns 64-bit integers.

Python tests cannot run here: the `.venv` was built for Python 3.12 and the
system now only has 3.14. See §7.

### 2.3 Build the images

```bash
make docker      # builds all three as openrouter/<svc>:dev
```

Or individually:

```bash
docker build -t openrouter/gateway-go:dev      gateway-go
docker build -t openrouter/backend-python:dev  backend-python
docker build -t openrouter/frontend-web:dev    frontend-web
```

Check them:

```bash
docker images --filter=reference='openrouter/*' \
  --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'

# Smoke-test the gateway binary without any dependencies
docker run --rm openrouter/gateway-go:dev --help 2>&1 | head -3 || true
```

---

## 3. Push to GitHub

Your remote is already set:
`https://github.com/RaviShankarRoy/openrouter.git`, branch `main`, one commit.

### 3.1 Confirm no secrets are going up

`.env` **is** gitignored and has **never** been committed — I verified with
`git log --all -- .env`. So the Google OAuth client secret in it stays local.
Confirm before every push anyway:

```bash
git status --short | grep -E '^\?\?.*\.env' && echo "UNTRACKED (good)"
git ls-files | grep -E '(^|/)\.env$' && echo "!!! TRACKED — STOP" || echo "clean"

# Broader sweep for anything key-shaped in what you are about to commit
git diff --cached -U0 | grep -nEi 'GOCSPX-|sk-[A-Za-z0-9]{20,}|whsec_|BEGIN [A-Z ]*PRIVATE KEY' \
  && echo "!!! secret in staged diff" || echo "staged diff clean"
```

> Separately: rotate that Google client secret when convenient. It is only on
> your disk, but it is a live credential sitting in a file you may one day
> `git add -f`.

### 3.2 Commit and push

```bash
git add -A
git status --short          # read this properly before committing

git commit -m "Fix container builds and add minikube overlay

- Add .dockerignore for backend-python (7.4GB context -> 2.4MB) and gateway-go
- Move sentence-transformers to an optional [ml] extra (image 8.9GB -> 720MB)
- Replace eval-based dynamic import in instrumentation.ts (Edge runtime ban)
- Fix 16 TypeScript errors blocking the Next.js production build
- Correct server-action auth field (backendJwt) and /v1 key paths
- Add frontend-web/public/ required by the Dockerfile
- Add infrastructure/kubernetes/overlays/minikube"

git push -u origin main
```

If the remote already has commits yours do not descend from:

```bash
git pull --rebase origin main    # replay your work on top
git push -u origin main
```

Never `--force` a shared branch. If the remote is empty or was only
initialised with a README, `git push -u origin main` just works.

### 3.3 Watch CI

`.github/workflows/ci.yml` runs only the stacks that changed
(`dorny/paths-filter`), generates proto stubs, then runs golangci-lint,
`go test -race`, pytest against real Postgres + Valkey service containers, and
the frontend suite.

```bash
gh run watch          # or open the Actions tab
```

Expect the Go job to fail on the miniredis test noted in §2.2 until that
assertion is changed.

---

## 4. Push to Docker Hub

### 4.1 Log in and set your namespace

```bash
export DOCKERHUB_USER=ravishankarroy     # your Docker Hub username
docker login -u "$DOCKERHUB_USER"        # use an access token, not your password
```

Create the access token at Docker Hub → Account Settings → Personal access
tokens, scope **Read & Write**. Tokens are revocable; your password is not.

### 4.2 Tag

Tag twice: an immutable version tag for traceability and `dev` as the moving
pointer the minikube overlay uses.

```bash
export VERSION=0.1.0

for svc in gateway-go backend-python frontend-web; do
  docker tag openrouter/$svc:dev  $DOCKERHUB_USER/$svc:$VERSION
  docker tag openrouter/$svc:dev  $DOCKERHUB_USER/$svc:dev
done

docker images --filter=reference="$DOCKERHUB_USER/*" \
  --format '{{.Repository}}:{{.Tag}}\t{{.Size}}'
```

### 4.3 Check before you push

```bash
# Does it actually start? (gateway exits without Redis — that is expected,
# you are checking the binary runs and reads config, not that it serves.)
docker run --rm $DOCKERHUB_USER/gateway-go:$VERSION 2>&1 | head -5

# Confirm the Python image is slim and has no CUDA
docker run --rm $DOCKERHUB_USER/backend-python:$VERSION \
  sh -c 'du -sh /opt/venv | cut -f1; ls /opt/venv/lib/python3.12/site-packages | grep -c nvidia || echo "0 nvidia packages"'

# Confirm the frontend image contains a standalone server
docker run --rm $DOCKERHUB_USER/frontend-web:$VERSION ls -la /app/server.js

# Vulnerability scan (the repo's docker.yml workflow gates on CRITICAL)
docker scout cves $DOCKERHUB_USER/backend-python:$VERSION 2>/dev/null \
  || docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
       aquasec/trivy image --severity HIGH,CRITICAL $DOCKERHUB_USER/backend-python:$VERSION
```

### 4.4 Push  *(untested — needs your credentials)*

```bash
for svc in gateway-go backend-python frontend-web; do
  docker push $DOCKERHUB_USER/$svc:$VERSION
  docker push $DOCKERHUB_USER/$svc:dev
done
```

Verify they landed:

```bash
for svc in gateway-go backend-python frontend-web; do
  echo "== $svc"
  docker manifest inspect $DOCKERHUB_USER/$svc:$VERSION | head -5
done
```

> **Repository visibility.** New Docker Hub repos are public by default. If you
> want them private, create each repo in the UI as private *before* the first
> push — and then minikube needs an `imagePullSecret` (§5.6).

---

## 5. Deploy to minikube

### 5.1 Start the cluster

The stack needs roughly 3 CPU and 5 GB once everything schedules. Give it
headroom:

```bash
minikube start --cpus=4 --memory=8192 --disk-size=40g --driver=docker
minikube addons enable ingress          # nginx ingress controller
minikube addons enable metrics-server   # required or every HPA reads <unknown>
kubectl get nodes
```

### 5.2 Point the overlay at your images

The overlay ships with a `DOCKERHUB_USER` placeholder.

```bash
cd infrastructure/kubernetes/overlays/minikube
sed -i "s/DOCKERHUB_USER/$DOCKERHUB_USER/g" kustomization.yaml
grep newName kustomization.yaml          # confirm
cd -
```

### 5.3 Render before you apply

Always look at what you are about to create.

```bash
kustomize build infrastructure/kubernetes/overlays/minikube > /tmp/mk.yaml
wc -l /tmp/mk.yaml                       # ~2043 lines
grep '^kind:' /tmp/mk.yaml | sort | uniq -c | sort -rn
grep 'image:' /tmp/mk.yaml | sort -u
```

You should see exactly your three Docker Hub images plus
`pgvector/pgvector:pg16`, `valkey/valkey:7.2-alpine`, `nats:2.10-alpine`.

### 5.4 Apply

```bash
kubectl apply -k infrastructure/kubernetes/overlays/minikube
kubectl -n openrouter get pods -w
```

Bring-up order matters: postgres, redis and nats must be Ready before the
backend's readiness probe passes, and the gateway needs the backend for its
own `/ready`. Give it two or three minutes.

### 5.5 Run the database migrations

Nothing runs Alembic automatically — no init container, no Job. Do it once by
hand after Postgres is Ready:

```bash
kubectl -n openrouter wait --for=condition=ready pod -l app.kubernetes.io/name=postgres --timeout=180s

kubectl -n openrouter exec -it deploy/backend-python -- \
  alembic upgrade head

# Confirm the schema
kubectl -n openrouter exec -it deploy/backend-python -- \
  python -c "import asyncio,asyncpg,os; \
print(asyncio.run(asyncpg.connect(os.environ['POSTGRES_DSN'].replace('+asyncpg','')).fetch \
  ('select tablename from pg_tables where schemaname=\'public\'')))" 2>/dev/null \
  || kubectl -n openrouter exec -it sts/postgres -- psql -U openrouter -d openrouter -c '\dt'
```

### 5.6 Private repos only — image pull secret

Skip if your Docker Hub repos are public.

```bash
kubectl -n openrouter create secret docker-registry dockerhub \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username="$DOCKERHUB_USER" \
  --docker-password='<access-token>'

kubectl -n openrouter patch serviceaccount default \
  -p '{"imagePullSecrets":[{"name":"dockerhub"}]}'
kubectl -n openrouter rollout restart deploy
```

### 5.7 Reach it

```bash
echo "$(minikube ip) openrouter.local" | sudo tee -a /etc/hosts

curl -i http://openrouter.local/api/health
curl -s http://openrouter.local/api/ready | jq
open http://openrouter.local           # the dashboard
```

Or bypass ingress entirely while debugging:

```bash
kubectl -n openrouter port-forward svc/gateway-go 8080:80 &
kubectl -n openrouter port-forward svc/backend-python 8000:8000 &
curl -s localhost:8080/ready | jq
curl -s localhost:8000/ready | jq
```

### 5.8 Iterating without Docker Hub

Once the cluster is up, skip the registry round trip entirely:

```bash
docker build -t $DOCKERHUB_USER/gateway-go:dev gateway-go
minikube image load $DOCKERHUB_USER/gateway-go:dev
kubectl -n openrouter rollout restart deploy/gateway-go
```

`imagePullPolicy` is `IfNotPresent` in the manifests, so a loaded image is used
without contacting the registry.

---

## 6. Verify the deployment

```bash
kubectl -n openrouter get all
kubectl -n openrouter get pods -o wide
kubectl -n openrouter describe pod -l app.kubernetes.io/name=gateway-go | tail -30
kubectl -n openrouter logs -l app.kubernetes.io/name=gateway-go --tail=50
kubectl -n openrouter logs -l app.kubernetes.io/name=backend-python --tail=50

# Events are where scheduling and pull failures actually show up
kubectl -n openrouter get events --sort-by=.lastTimestamp | tail -25

# Prove the gateway reaches the backend over gRPC
kubectl -n openrouter exec -it deploy/gateway-go -- /gateway --help 2>/dev/null || \
kubectl -n openrouter run grpc-probe --rm -it --restart=Never \
  --image=$DOCKERHUB_USER/gateway-go:dev --command -- /gateway 2>&1 | head
```

End-to-end, once you have seeded a key:

```bash
kubectl -n openrouter exec -it deploy/backend-python -- python seed_dev.py
# copy the printed sk-or-v1-... key
curl -sS http://openrouter.local/api/v1/chat/completions \
  -H "Authorization: Bearer sk-or-v1-..." \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: smoke-1' \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}' -D-
```

That last call needs a real `OPENAI_API_KEY` reachable by the gateway pod. The
manifests do not inject provider keys — add them to
`overlays/minikube/secrets.yaml` and reference them in the gateway deployment,
or expect a 503 from the fallback chain.

---

## 7. Things that will bite you

| Symptom | Cause | Fix |
|---|---|---|
| `make proto` fails on `grpc_tools` | The Python venv was built for 3.12; the box only has 3.14, so `site-packages` no longer resolves | Recreate it: `cd backend-python && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"` |
| Python tests will not run | Same broken venv | Same fix |
| `postgres` pod `CreateContainerConfigError` | You applied the `dev` overlay, not `minikube` — base uses Spilo/Patroni, which reads a `openrouter-postgres-bootstrap` secret nothing creates, and needs RBAC for its Kubernetes DCS | Use `overlays/minikube`, which replaces it with plain `pgvector/pgvector:pg16` |
| Pods `Pending`, `Insufficient cpu` | minikube too small | `minikube stop && minikube start --cpus=4 --memory=8192` |
| HPA shows `<unknown>/2000` | metrics-server not enabled, and the custom RPS metric needs prometheus-adapter, which is not installed | Enable metrics-server; ignore the RPS target locally |
| `ImagePullBackOff` | Placeholder not replaced, or private repo without a pull secret | §5.2 and §5.6 |
| Ingress 404 | Ingress addon not ready, or `/etc/hosts` missing | `kubectl -n ingress-nginx get pods`; re-check §5.7 |
| Gateway `/ready` returns 503 | Redis or the backend gRPC is not up yet | `kubectl -n openrouter get pods`; the readiness probe is honest, wait for it |
| Celery worker CrashLoop | Was a wrong module path in the manifests; the recent restructure already corrected it to `app.repository.celery_app` | Verify with `kubectl -n openrouter logs deploy/backend-celery-worker` |
| `/v1/models` returns `{"data": []}` | `register_providers()` is never called from the FastAPI lifespan — only from a test | One line in `app/main.py`'s `lifespan()` |
| No metrics on `:9091` | All seven Prometheus collectors are declared and never incremented | Known gap; see the Connection Atlas §6.3 |

---

## 8. The short version

```bash
# build
make proto && make docker

# github
git add -A && git commit -m "..." && git push -u origin main

# docker hub
export DOCKERHUB_USER=... VERSION=0.1.0
docker login -u "$DOCKERHUB_USER"
for s in gateway-go backend-python frontend-web; do
  docker tag openrouter/$s:dev $DOCKERHUB_USER/$s:$VERSION
  docker tag openrouter/$s:dev $DOCKERHUB_USER/$s:dev
  docker push $DOCKERHUB_USER/$s:$VERSION && docker push $DOCKERHUB_USER/$s:dev
done

# minikube
minikube start --cpus=4 --memory=8192 --driver=docker
minikube addons enable ingress metrics-server
sed -i "s/DOCKERHUB_USER/$DOCKERHUB_USER/g" infrastructure/kubernetes/overlays/minikube/kustomization.yaml
kubectl apply -k infrastructure/kubernetes/overlays/minikube
kubectl -n openrouter wait --for=condition=ready pod -l app.kubernetes.io/name=postgres --timeout=180s
kubectl -n openrouter exec -it deploy/backend-python -- alembic upgrade head
echo "$(minikube ip) openrouter.local" | sudo tee -a /etc/hosts
curl -i http://openrouter.local/api/health
```
