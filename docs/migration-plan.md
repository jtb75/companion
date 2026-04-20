# Companion: Self-Hosted Migration Plan

Migrating from Google Cloud / Firebase to a self-hosted Kubernetes cluster,
with local LLM inference via Ollama on dedicated bare-metal Mac Studios.

**Architecture tiers:**
- **Inference tier:** 2× Mac Studio (M4 Max 64GB + M3 Ultra 96GB, 10GbE) running
  Ollama on bare metal. No K8s. Dedicated to LLM + embeddings.
- **Compute tier:** 3-node K3s cluster on Minisforum AI X1-255 (Ryzen 7 255,
  64GB DDR5-5600, 2× 1TB NVMe, 2.5GbE). Hosts everything else.

**Status:** Draft, 2026-04-19. Revised 2026-04-19 after landing 3-node compute
architecture + Longhorn storage decisions. Decisions log at the end.

---

## 1. Summary

**From:** Cloud Run + Cloud SQL + Memorystore + GCS + Pub/Sub + Cloud Scheduler
+ Vertex AI (Gemini) + Document AI + Cloud TTS/STT + Cloud KMS + Firebase Auth
+ Firebase Cloud Messaging + Firestore.

**To:** 3-node K3s cluster (Minisforum AI X1-255) with Longhorn for block storage,
CNPG Postgres on Longhorn volumes, in-cluster Redis, in-cluster MinIO, in-process
events, K8s CronJobs. Ollama on two bare-metal Mac Studios (Metal GPU access).
Local OCR, Piper TTS, faster-whisper STT, app-level AES encryption, Authentik
for auth, Redis pub/sub + SSE for real-time. Push via APNs-direct + WebSocket.

**Strategy:** Migrate, not rebuild. The GCP integrations are at the edges
(integrations/, services/kms_service.py, conversation/tts.py, events/publisher.py,
notifications/channels.py). The domain logic — pipeline, safety layer, caregiver
tiers, prompt engineering, conversation state — is vendor-neutral Python and stays.

**Phasing:** 12 phases, each shippable and reversible on its own. Phases 0-2 are
strictly sequential (foundation). Phases 3-10 can parallelize. Phases 11-12
close the loop.

---

## 2. Target architecture

```
                        Cloudflare Tunnel (*.mydailydignity.com)
                                    |
                              Traefik (on K3s cluster)
          /         /          |            \              \
    auth.mdd   api.mdd    app.mdd       argocd.mdd   (other ingresses)
       |          |           |
    Authentik   Companion   Companion
                backend     web
                   |
                   +--- http://ollama.llm.svc.cluster.local:11434
                                      |
                              (Service, no selector)
                              (manual Endpoints)
                                  /        \
                   192.168.0.94:11434   192.168.0.104:11434
                   studio-max (M4 Max)  studio-ultra (M3 Ultra)
                   ---- Inference tier (bare metal, 10GbE) ----

---- Compute tier: K3s on 3× Minisforum AI X1-255 (2.5GbE) ----

   Per node (AMD Ryzen 7 255, 64GB DDR5-5600, dual NVMe):
     - Disk 1 (1TB): OS (Debian/Ubuntu LTS) + K3s + container cache
     - Disk 2 (1TB): Longhorn data disk (replicated volumes)

   Cluster-wide:
     - K3s in HA (3 control plane nodes, embedded etcd)
     - Argo CD (gitops — reads from github.com/jtb75/argocd-apps)
     - Traefik (Ingress via Cloudflare Tunnel, plain HTTP inside)
     - Sealed Secrets controller
     - Longhorn (3-replica block storage, one replica per node)
     - CloudNativePG operator (Postgres on Longhorn volumes)
     - MinIO (single-pod on Longhorn, S3 API + CNPG backup target)
     - Redis (per-app namespace)
     - Zot registry
     - Authentik + its CNPG cluster + its Redis
     - Companion backend + web + workers
     - Observability: Grafana + Loki + Prometheus (Phase 10)
     - (Existing workloads — sonarr/radarr/Plex/mail-relay — migrate from
        the old OrbStack K3s during the cutover window)

---- Retained dependencies (intentional) ----

  - Apple APNs relay for iOS push (physics — not self-hostable)
  - Google OIDC as an optional upstream IdP in Authentik (local accounts also work)
  - Cloudflare Tunnel + DNS (*.mydailydignity.com)
  - GitHub (source + CI)
  - NAS (nas.ng20.org) demoted to bulk-only: Plex/media library,
    restic offsite backups. NOT in the critical path for Companion.
```

**Domain convention:**

| Domain | Purpose |
|---|---|
| `ng20.org` | Shared infrastructure — one IdP, one registry, one object store, one Argo, one Grafana serving all products |
| `mydailydignity.com` | Companion (D.D.) product — mobile app, web, API |
| `silkstrand.io` | Silkstrand product |

Shared infrastructure is tenant-agnostic. Products consume it. A product's
domain hosts only that product's user-facing surfaces.

**Shared infrastructure endpoints:**

| Service | Domain | Scope | External ingress? | Auth |
|---|---|---|---|---|
| Argo CD | `argocd.ng20.org` | Cluster gitops | Yes (via Tunnel) | OIDC via Authentik (Phase 1 follow-up) |
| Authentik | `auth.ng20.org` | IdP for all tenants | Yes (via Tunnel) | Local + Google OIDC upstream |
| Zot registry | `zot.ng20.org` | Container images for all tenants | Yes (via Tunnel) | OIDC via Authentik |
| MinIO (S3 API) | `s3.ng20.org` | External S3 callers only (restic, off-cluster scripts) | Optional (Phase 0 follow-up) | Per-tenant IAM users |
| MinIO (console) | `s3-console.ng20.org` | Admin UI | Yes (via Tunnel) | OIDC via Authentik |
| MinIO (in-cluster) | `minio.minio.svc.cluster.local:9000` | All in-cluster S3 consumption | No — internal only | Per-tenant IAM users |
| Grafana | `grafana.ng20.org` | Observability | Yes (via Tunnel) | OIDC via Authentik (Phase 10) |

**Authentik as the shared IdP:**

Deployed in `authentik` namespace. Serves:
- **Companion** (mydailydignity.com) — OIDC client, PKCE flow
- **Silkstrand** (silkstrand.io) — future OIDC client (not covered in this plan)
- **ng20.org tools** — Argo, Zot, MinIO console, Grafana via OIDC; Plex /
  Sonarr / Radarr / nzbget via Traefik forward-auth + Authentik Outpost

Single user directory, single MFA policy, per-app access control via Authentik
Groups. Group naming: `<tenant>:<role>` — e.g., `companion:caregiver-tier-1`,
`silkstrand:admin`, `infra:admin`, `plex:user`.

**MinIO as the shared object store:**

Deployed in `minio` namespace. Primary consumption is in-cluster via ClusterIP
(`minio.minio.svc.cluster.local:9000`) — fast, no Cloudflare hop. External
access limited to the console UI and (optionally) the S3 API for off-cluster
callers.

Per-tenant IAM, not shared root credentials:
- `companion-backend` — scoped to `companion-*` buckets
- `cnpg-backup` — scoped to `cnpg-backups/*` (all Postgres clusters)
- `restic-offsite` — scoped to `restic-offsite`
- `silkstrand-*` — slot ready for when Silkstrand onboards
- root creds — break-glass only, SealedSecret stays, apps never use it

Bucket naming: `<tenant>-<purpose>` (e.g., `companion-documents`,
`companion-archives`). Cross-tenant buckets allowed when clearly shared (e.g.,
`cnpg-backups` with per-cluster path prefixes).

**Bare-metal Ollama hardening (per Mac):**
- Bound to `0.0.0.0:11434` via launchd LaunchDaemon
- `OLLAMA_KEEP_ALIVE=24h`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`
- Logs to `/Users/joe/Library/Logs/ollama.{log,err}`
- Runs as user `joe`, survives reboots

**Failure domains:**
- One Minisforum offline: Longhorn 3-replica keeps volumes available (2 of 3 replicas remain), K3s etcd keeps quorum (2 of 3 control planes).
- One Mac offline: Ollama Service has 1 remaining endpoint, kube-proxy routes to it. Inference continues at reduced capacity.
- NAS offline: only media + backups impacted. Companion keeps running.

**Components that still touch Google (intentional):**
- **APNs relay** for iOS background push. Apple's infra — not self-hostable.
- **Google OIDC** as upstream social-login option in Authentik. Optional; local accounts are the primary path.

---

## 3. Repository strategy

**Single GitOps repo: `~/repo/argocd-apps`** (github.com/jtb75/argocd-apps).
Already driving Argo. Conventions in place:
- `applications/*.yaml` — Argo `Application` CRDs
- `infra/<name>/` — raw K8s manifests

**Delete** `~/repo/companion-gitops` (scaffold created in error before the existing repo was known).

**Repurpose** `~/repo/authentik-gitops/manifests/` — ~80% reusable. Changes:
- Swap `Ingress` (nginx class) → Traefik `IngressRoute`
- Remove cert-manager annotations (Cloudflare Tunnel terminates TLS)
- Rename domain `sso.k8s.ng20.org` → `auth.ng20.org`
- Regenerate sealed secrets for this cluster

**New subdirectories in argocd-apps:**
- `infra/longhorn/` — Longhorn distributed block storage
- `infra/cnpg-operator/` — CNPG operator (via Argo Helm source)
- `infra/minio/` — MinIO deployment backed by Longhorn volume
- `infra/authentik/` — copied and adapted from authentik-gitops
- `infra/companion-db/` — CNPG `Cluster` CR for companion Postgres
- `infra/companion-redis/` — in-cluster Redis for companion
- `infra/ollama-endpoints/` — K8s Service + Endpoints pointing at bare-metal Ollama
- `companion/base/` + `companion/overlays/{staging,prod}/` — app Kustomize

**New Applications:**
- `applications/longhorn.yaml`
- `applications/cnpg-operator.yaml`
- `applications/minio.yaml`
- `applications/authentik.yaml`
- `applications/companion-db.yaml`
- `applications/companion-redis.yaml`
- `applications/companion-staging.yaml`
- `applications/companion-prod.yaml` (later)

**Previous iteration (on the old OrbStack K3s, 2026-04-19):**
The Phase 0 scaffold already committed to `argocd-apps` — `cnpg-operator.yaml`,
`minio.yaml`, `ollama-endpoints.yaml`, `infra/minio/`, `infra/ollama-endpoints/` —
targeted the now-deprecated 2-node OrbStack cluster. The *manifests* are mostly
correct for the new cluster too, with one change:

- `infra/minio/pvc.yaml` — change `storageClassName: nfs-client` → `longhorn`.
  Everything else (namespace, Deployment, Service, SealedSecret) carries over.

The sealed secret (`infra/minio/sealed-secret.yaml`) was sealed against the OLD
cluster's sealed-secrets controller key. On the NEW cluster it must be re-sealed
— re-run the procedure in `infra/minio/README.md`.

The `ollama-endpoints` manifests (Service + manual Endpoints pointing at
192.168.0.94 and 192.168.0.104) apply unchanged — Ollama on the Macs hasn't
moved.

---

## 4. Open decisions (block phases as noted)

| # | Decision | Options | Recommended | Blocks |
|---|---|---|---|---|
| D1 | Primary LLM model | Qwen 2.5 32B / Llama 3.3 70B / Qwen 2.5 72B | Qwen 2.5 32B (best function-calling/size ratio). Runs on studio-ultra (96GB). | Phase 3 |
| D2 | Embedding model | bge-m3 (1024) / nomic-embed-text (768) / mxbai-embed-large (1024) | bge-m3, served by studio-max (64GB) | Phase 3, Phase 2 schema |
| D3 | Push notifications | FCM HTTP v1 direct / APNs direct (iOS only) / WebSocket-only foreground | Hybrid: APNs direct (iOS) + WebSocket (Android foreground) | Phase 8 |
| D4 | OCR engine | PaddleOCR / Surya / VLM via Ollama (Qwen2-VL) | PaddleOCR first; evaluate VLM for the extraction pass only | Phase 7 |
| D10 | Offsite backup destination | Second NAS / Backblaze B2 / rsync to external USB | B2 or equivalent cloud object (NAS failure survival requires a non-NAS target) | Phase 10 |

**Decisions settled since last revision** (now in §6 Decisions log): cluster
architecture (3-node Minisforum + Macs-as-Ollama-only), storage (Longhorn
3-replica), Authentik DB on CNPG (D5), mobile reachability via Cloudflare
Tunnel (D6), real-time transport SSE + Redis pub/sub (D7), intra-cluster
TLS plain HTTP (D8), observability via kube-prometheus-stack + Loki (D9).

---

## 5. Phase plan

Effort: S = <1 day, M = 1-3 days, L = 3-7 days, XL = >1 week.
Risk: L/M/H.

| Phase | Goal | Deps | Effort | Risk |
|---|---|---|---|---|
| **-1** | **Bring up the 3-node K3s cluster on Minisforums** | — | M | L |
| 0 | GitOps foundation on new cluster: Longhorn, CNPG operator, MinIO, Ollama networking | -1 | M | L |
| 1 | Authentik identity provider, end-to-end with a test app | 0 | M | M |
| 2 | Companion Postgres (CNPG on Longhorn + pgvector) + Redis | 0 | S | L |
| 3 | Ollama client in backend + model selection + tool-calling | 0 | M | M |
| 4 | Object storage swap (GCS → MinIO) in backend | 0, 2 | S | L |
| 5 | Auth cutover (Firebase → Authentik OIDC) in backend | 1, 2 | L | H |
| 6 | Voice stack (Piper TTS + faster-whisper STT) | 0 | M | M |
| 7 | OCR engine (Document AI → PaddleOCR) | 0 | M | H |
| 8 | Real-time sync (Firestore → SSE) + push notifications | 0, 2 | L | H |
| 9 | Field-level encryption (Cloud KMS → app AES) | 2 | S | M |
| 10 | Observability (Grafana + Loki + Prometheus) | 0 | M | L |
| 11 | Mobile app rebuild (Authentik auth + push swap + config) | 5, 8 | L | H |
| 12 | Staging cutover, soak, production flip, GCP teardown | all | M | H |

---

### Phase -1 — Bring up the 3-node K3s cluster

**Goal:** Three Minisforums running Debian/Ubuntu LTS + K3s in HA (3 control
plane nodes with embedded etcd), cabled on the 10GbE switch at 2.5GbE, with
Argo CD, Traefik, Cloudflared, Sealed Secrets installed and driven from
`argocd-apps`.

**Prerequisites (order before hardware arrives):**
- 3× Minisforum AI X1-255 barebones ordered
- 3× 64GB DDR5-5600 SODIMM kits (Crucial, Kingston Fury, or equivalent)
- 6× 1TB NVMe PCIe 4.0 SSDs (Samsung 990 EVO, WD Black SN770, Crucial T500) — OS + Longhorn data disk per node
- 3× Cat 6 cables to the 10GbE switch
- USB stick for Linux install media

**Steps:**

1. **Assemble the Minisforums.** Open each, install 64GB RAM (both SODIMM slots), install 2× NVMe (OS in slot 1, Longhorn data in slot 2). ~15 min per unit.

2. **Install the OS.** Debian 12 LTS or Ubuntu 24.04 LTS. Minimal install (no desktop). Configure:
   - Static IP or DHCP reservation per node on the 10GbE switch subnet
   - SSH key auth, disable password login
   - Hostnames: `k3s-01`, `k3s-02`, `k3s-03` (or similar)
   - Install `open-iscsi` (Longhorn prereq), `nfs-common` (if mounting NAS for bulk)
   - Second NVMe left unformatted — Longhorn will claim it as a raw disk

3. **Install K3s in HA mode.**
   - Node 1: `k3s server --cluster-init --write-kubeconfig-mode 644 --disable traefik --disable servicelb`
   - Nodes 2 & 3: `k3s server --server https://<k3s-01>:6443 --token <cluster-token> --disable traefik --disable servicelb`
   - `--disable traefik` because we'll install our own via Argo (matches current convention)
   - Verify: `kubectl get nodes` shows 3 Ready control-plane nodes
   - Copy `/etc/rancher/k3s/k3s.yaml` to local `~/.kube/config` (fix the server URL to a LAN-reachable hostname)

4. **Bootstrap cluster essentials.** Apply (outside Argo, one-time):
   - Sealed Secrets controller — same as old cluster, in `infra` namespace. NOTE: generates a NEW sealing key — all sealed secrets from the old cluster must be re-sealed.
   - Argo CD (via Helm or manifest) in `argocd` ns.

5. **Point Argo at the gitops repo.** `kubectl apply -f ~/repo/argocd-apps/root-app.yaml`. Argo picks up the Applications dir and starts syncing.

6. **Reconcile the application set.** Remove or update Applications that no longer apply to the new cluster. In particular:
   - Keep: `traefik`, `cloudflared`, `sealed-secrets-controller`, `nfs-subdir-provisioner` (for bulk NAS), `zot`, `argocd-ingress`, `ollama-endpoints` (with re-sealed creds where needed)
   - Add: `longhorn`, `cnpg-operator`, `minio` (with re-sealed `minio-root`)
   - Decide: media stack (`media`, `mail-relay`) — migrate from old cluster now or later?

7. **Cloudflare Tunnel routes.** Update the Tunnel config on the new cluster's cloudflared to route `argocd.*`, `auth.*`, `api.*`, `app.*` to the new Traefik Service.

8. **Decommission strategy for the old OrbStack cluster.** Two paths:
   - **Wholesale cutover:** migrate all workloads, delete OrbStack K3s, Macs become Ollama-only.
   - **Staged:** run both clusters in parallel; move Companion workloads to new; leave media apps on old until convenient.
   - Recommend staged — lower risk.

**Validation:**
- `kubectl get nodes` → 3 Ready, all roles `control-plane,master`
- `kubectl get pods -A` → argocd, sealed-secrets, traefik, cloudflared all Running
- `kubectl get applications -n argocd` → everything Synced + Healthy (or reasonable Progressing)
- `curl https://argocd.mydailydignity.com` → Argo UI loads through new Tunnel

**Rollback:** keep the old OrbStack cluster alive until the new one is green for a week. DNS/tunnel flip is the only hard cutover.

**Risks:**
- **Sealed secrets re-sealing.** Every sealed secret from the old cluster is encrypted with a key that doesn't exist in the new cluster. Inventory them, regenerate plaintext, re-seal. Document the plaintext inventory somewhere out-of-cluster (1Password).
- **K3s HA quirks.** Embedded etcd in 3-node K3s is solid but recovery from a split-brain is painful. `etcd-io/etcd` tools work but have a learning curve.
- **Mac Ollama reachability.** Minisforums are on (probably) a different subnet from the Macs' 10GbE. Verify pod→Mac routing works end-to-end before claiming Phase -1 is done.

---

### Phase 0 — Storage, operator, object store, LLM networking

**Goal:** Longhorn running with 3 replicas. CNPG operator installed (no clusters
yet). MinIO serving S3 API on a Longhorn-backed volume. Ollama reachable as a
cluster Service. Nothing Companion-specific yet.

**Steps:**

1. **Deploy Longhorn via Argo.**
   - `applications/longhorn.yaml` — Helm source `https://charts.longhorn.io`, chart `longhorn`, namespace `longhorn-system`
   - Values: `defaultReplicaCount: 3`, set `defaultDataPath` to where the second NVMe is mounted on each node (e.g., `/var/lib/longhorn`), enable automatic replica rebalancing
   - After sync: create `StorageClass` named `longhorn` (or confirm chart's default), set it as the cluster's default storage class
   - Longhorn UI exposed via port-forward only (no external ingress)

2. **Deploy CNPG operator.**
   - `applications/cnpg-operator.yaml` — Helm source `https://cloudnative-pg.github.io/charts`, chart `cloudnative-pg`, namespace `cnpg-system`
   - No clusters yet — operator only. Authentik and Companion will create their CNPG `Cluster` CRs in Phase 1/2.

3. **Deploy MinIO as shared object store.**
   - `applications/minio.yaml` + `infra/minio/` — adapted from the previous-iteration manifests. Change `storageClassName` on the PVC from `nfs-client` → `longhorn`. Re-seal the root credentials against the new cluster's sealing key.
   - Bucket provisioning Job (one-shot): creates `companion-documents`, `companion-archives`, `cnpg-backups`, `restic-offsite`. Silkstrand buckets created when that tenant onboards.
   - **Per-tenant IAM users** (Job or `mc` bootstrap):
     - `companion-backend` — policy: R/W on `companion-*` buckets
     - `cnpg-backup` — policy: R/W on `cnpg-backups/*` (path prefixes per cluster)
     - `restic-offsite` — policy: R/W on `restic-offsite`
   - Each user's access key + secret stored as a SealedSecret scoped to the consuming tenant's namespace (`companion/minio-credentials`, etc.). Root creds remain break-glass only.
   - **Console ingress** at `s3-console.ng20.org` — Traefik `IngressRoute` with Authentik forward-auth middleware (wired up in Phase 1 follow-up once Authentik is live; until then, port-forward).
   - **S3 API external ingress** at `s3.ng20.org` (optional, deferred to Phase 10 when we add restic-offsite from the NAS). In-cluster consumers always use the internal ClusterIP.
   - Cloudflare Tunnel: add routes for `s3-console.ng20.org` and (optionally) `s3.ng20.org`.

4. **Re-apply Ollama endpoints.**
   - `applications/ollama-endpoints.yaml` + `infra/ollama-endpoints/` — unchanged from previous iteration. Service in `llm` namespace, manual Endpoints pointing at `192.168.0.94` and `192.168.0.104`.
   - *Known workaround:* Argo silently skipped the `endpoints.yaml` file on the old cluster. After Argo syncs, run `kubectl apply -f infra/ollama-endpoints/endpoints.yaml` manually and investigate root cause separately.

5. **Pull target models on Macs** (work that happens outside the cluster, in parallel):
   - `ollama pull qwen2.5:32b-instruct-q4_K_M` on studio-ultra
   - `ollama pull bge-m3` on studio-max
   - Warm both with a dummy request so first-use latency is acceptable.

**Validation:**
- `kubectl -n longhorn-system get pods` → all Running
- `kubectl get sc` → `longhorn` listed, marked default
- Create a test PVC with `storageClassName: longhorn`, attach to a toy Pod, write data, delete Pod, reattach — data persists.
- Kill a Longhorn replica pod — rebuild on another node visible in Longhorn UI within seconds.
- `kubectl -n cnpg-system get pods` → operator running
- MinIO health endpoint responds: `curl http://minio.minio.svc.cluster.local:9000/minio/health/live`
- Ollama endpoint responds through the Service: `curl http://ollama.llm.svc.cluster.local:11434/api/tags` returns list including `qwen2.5:32b-instruct-q4_K_M` and `bge-m3`.

**Rollback:** delete the four Applications; Argo reaps all resources. Longhorn data on second NVMes can be wiped to reclaim.

**Risks:**
- **Longhorn first-boot on a fresh disk.** Make sure each node's second NVMe is discovered, formatted as `ext4` mounted at the right path, and writable before Longhorn tries to claim it. `/etc/fstab` entries with `nofail` so a missing disk doesn't block boot.
- **Longhorn + K3s + SELinux.** If on a distro with SELinux enforcing (RHEL/Rocky), extra policy config needed. On Debian/Ubuntu, no issue.
- **open-iscsi service must be enabled on every node.** Longhorn uses iSCSI internally to expose volumes to pods. Easy to forget.

---

### Phase 1 — Authentik (shared-infrastructure SSO)

**Goal:** Authentik running at `auth.ng20.org` as the shared IdP for all current
and future tenants. Local accounts + Google OIDC upstream. A test OIDC app
("companion-test") configured so we can validate PKCE flow end-to-end before the
real backend depends on it. Additional tenants (Silkstrand, homelab tools)
onboard incrementally in later phases — the Authentik deployment itself is
tenant-agnostic.

**Tenant/integration plan (roadmap, not all in this phase):**

| Tenant | Integration | Phase |
|---|---|---|
| Companion (mydailydignity.com) | OIDC + PKCE | Phase 1 (test app), Phase 5 (real cutover) |
| Argo CD | OIDC | Phase 1 follow-up — drops the default admin password |
| Silkstrand (silkstrand.io) | OIDC | Out of scope for this plan; slot ready |
| Grafana | OIDC | Phase 10 (when observability lands) |
| MinIO console | OIDC | Phase 0 follow-up (optional) |
| Zot registry | OIDC | Phase 0 follow-up (optional) |
| Plex / Sonarr / Radarr / nzbget | Traefik forward-auth + Authentik Outpost | After primary migration — "homelab SSO" pass |

Access scoping per tenant via Authentik Groups. Companion's caregiver-tier
model (`companion:caregiver-tier-1`, etc.) is just one tenant's namespace.

**Steps:**
1. Copy `~/repo/authentik-gitops/manifests/` → `argocd-apps/infra/authentik/`.
2. Adapt:
   - Remove `postgresql/` StatefulSet — replace with a CNPG `Cluster` CR (3 instances on Longhorn, 10Gi per instance).
   - Keep `redis/` StatefulSet as a Deployment with a Longhorn PVC (small, 5Gi).
   - Ingress → Traefik `IngressRoute` on `auth.ng20.org`.
   - Drop cert-manager annotations (Cloudflare Tunnel terminates TLS).
   - Regenerate sealed secrets for the new cluster's sealing key:
     ```
     ./generate-secrets.sh
     kubeseal --format yaml < manifests/secrets-generated.yaml \
       --controller-namespace infra --controller-name sealed-secrets-controller \
       > infra/authentik/sealed-secrets.yaml
     ```
3. Cloudflare Tunnel: add ingress rule for `auth.ng20.org` → Traefik service.
4. `applications/authentik.yaml` — Argo Application pointing at `infra/authentik/`.
5. After sync:
   - Run the Authentik initial-setup flow at `/if/flow/initial-setup/` — create admin account.
   - Configure Google as OIDC upstream: Admin → Directory → Federation & Social Login → Create Google OAuth source. Need Google OAuth client ID + secret from a Google Cloud console project (one-time, even in self-hosted world).
   - Create "companion-test" OIDC Provider + Application with PKCE enabled.
   - (Follow-up, same phase if desired) wire Argo CD's OIDC config to Authentik — drops the default admin password.

**Validation:**
- Browse to `auth.ng20.org` → Authentik login UI with custom branding.
- Create a local account → log in → see user dashboard.
- Click "Continue with Google" → OAuth flow completes → new local user linked to Google identity.
- Test OIDC client: run a tiny OIDC CLI (e.g., `oidc-client-cli`) against the companion-test app. Confirm ID token validates, contains expected claims (`sub`, `email`, `groups` if configured).

**Rollback:** delete Application; CNPG cluster survives if desired (drop it manually).

**Risks:**
- Authentik's Postgres schema is version-sensitive. Pin Authentik chart/image version in the manifest; don't auto-update.
- Branding/CSS work is a rabbit hole — ship with default branding in Phase 1, iterate later.

---

### Phase 2 — Companion Postgres + Redis

**Goal:** A CNPG `Cluster` named `companion-db` (3 instances on Longhorn-backed volumes, one replica per node), `pgvector` extension enabled, Alembic migrations applied against an empty schema. Redis Deployment in `companion` namespace.

**Steps:**
1. `infra/companion-db/` — CNPG `Cluster` CR: 3 instances, `storageClass: longhorn`, 50Gi per instance, `postgresql.parameters.shared_preload_libraries = 'vector'`, `postInitSQL: CREATE EXTENSION IF NOT EXISTS vector;`. Anti-affinity: one replica per K8s node. Longhorn provides the underlying 3-replica block durability — CNPG layers its own streaming replication on top for HA failover.
2. `infra/companion-db/` — CNPG `ScheduledBackup` CR → MinIO bucket `cnpg-backups`. Barman-cloud config referencing a sealed MinIO access key. WAL archiving continuous.
3. `infra/companion-redis/` — Deployment + Service + PVC (small, 5Gi, `storageClass: longhorn`).
4. `applications/companion-db.yaml`, `applications/companion-redis.yaml`.
5. Create the companion database + user: post-init SQL or a one-shot Job.
6. Wire-up check from a test pod: `psql $DATABASE_URL -c 'SELECT 1'`.
7. Run Alembic migrations from a Job or `kubectl run --rm` with the backend image.

**Validation:**
- `kubectl -n companion exec -it pg-test -- psql -c '\dx'` shows `vector` extension.
- `kubectl logs -n companion deploy/redis` shows Redis ready.
- Alembic `current` matches `head`.
- Backups: force a manual backup, check MinIO has an object under `cnpg-backups/companion-db/base/`.

**Rollback:** drop the Applications. WARNING: PVC data persists unless explicitly deleted. Good default.

**Risks:**
- Streaming replica across Macs — if one Mac is down during a migration, CNPG's failover window is ~30s. Acceptable.
- pgvector embedding dimension depends on D2. If we pick bge-m3 (1024), the existing schema (assumes 768) needs a migration — Alembic needs a new revision before first deploy.

---

### Phase 3 — Ollama client in backend

**Goal:** New `OllamaClient` subclass of `LLMClient` in `backend/app/conversation/llm.py`, supporting generate / generate_stream / generate_with_tools. Config switch: `COMPANION_LLM_PROVIDER=ollama`. Embeddings endpoint swapped from Vertex to Ollama's `/api/embeddings`.

**Steps:**
1. Pull D1 + D2 models onto each Mac Studio via `ollama pull`.
2. Implement `OllamaClient` in `conversation/llm.py`:
   - `generate`: POST `/api/chat` with `{model, messages: [...], stream: false, options}`.
   - `generate_stream`: same endpoint, `stream: true`, parse NDJSON.
   - `generate_with_tools`: pass `tools` param (OpenAI-shaped function schemas). Parse `message.tool_calls` in response. Tool-calling models: Qwen 2.5, Llama 3.3.
3. Add `ollama_base_url` config setting (default `http://ollama.llm.svc.cluster.local:11434`). Factory `get_llm_client()` picks by provider.
4. Refactor `get_llm_client()` to include "ollama".
5. `pipeline/embeddings.py` currently uses Vertex `text-embedding-005`. Add an `OllamaEmbeddingsClient` + config switch `COMPANION_EMBEDDING_PROVIDER=ollama`.
6. Update Alembic — create a revision that changes the `document_chunks.embedding` column dimension to match D2. (Drop + recreate the column; re-embedding happens on next document ingest; for existing chunks, a backfill Job.)
7. Tool executor (`conversation/tool_executor.py`): add a branch that parses Ollama's tool-call format (which is closer to OpenAI than to Vertex). Gemini's format currently drives the parser — refactor to normalize to a shared shape.

**Validation:**
- Unit test: `OllamaClient.generate` returns non-empty text for a toy prompt.
- Integration test: one round-trip of a tool call using the companion tool schema — confirm the model emits a tool call, executor runs it, result is threaded back.
- Quality eval: run the pipeline classification stage against 20 sample documents with Ollama as the LLM. Compare to Gemini baseline — accuracy delta should be < 10%.
- Latency: p50 for a 500-token response under 4s on a single Mac Studio.

**Rollback:** set `COMPANION_LLM_PROVIDER=gemini`, revert the Alembic revision (if dimensions differ), redeploy.

**Risks:**
- **Function-calling reliability.** Local models are noisier at tool use than Gemini. Expect some prompt tuning in `conversation/persona.py` + retry logic in the tool loop.
- **Thinking-mode output.** Qwen/Llama don't have Vertex's thinking-config; the `disable_thinking` param becomes a no-op. Shouldn't hurt.
- **Cold start.** First request after Ollama starts pays model-load time (up to 30s for 32B). Run a warmup ping on pod startup.

---

### Phase 4 — Object storage swap

**Goal:** Backend reads and writes to MinIO instead of GCS. All `services/` calls that use `google.cloud.storage` swap to an S3-compatible client (aioboto3 or minio-py).

**Files touched:**
- `backend/app/pipeline/ingestion.py` — raw document upload
- `backend/app/services/image_analysis_service.py` — image upload
- `backend/app/services/account_lifecycle_service.py` — retention/deletion
- `backend/app/services/document_service.py` — document reads (confirm)
- `backend/app/conversation/tts.py` / `stt.py` — if any audio artifact writes

**Steps:**
1. Add `aioboto3` to `pyproject.toml`, drop `google-cloud-storage` (eventually — dual-stack during transition).
2. Introduce `backend/app/services/object_store.py` — a thin abstraction: `upload_bytes(path, data, content_type)`, `get_signed_url(path, expiry)`, `delete(path)`, `download_bytes(path)`. Backed by S3/MinIO via aioboto3.
3. Config: `COMPANION_S3_ENDPOINT=http://minio.minio.svc.cluster.local:9000`, `COMPANION_S3_ACCESS_KEY`, `COMPANION_S3_SECRET_KEY`, `COMPANION_S3_BUCKET_DOCUMENTS=companion-documents`. The access key + secret come from the **per-tenant `companion-backend` IAM user** created in Phase 0, not the MinIO root creds. SealedSecret lives in the `companion` namespace.
4. Replace call sites. Keep the method signatures on services the same.
5. Buckets (`companion-documents`, `companion-archives`) were pre-created in Phase 0 — nothing needed here beyond sanity-checking they exist and the `companion-backend` user has write access.

**Validation:**
- Upload a scan from the mobile app → appears in MinIO bucket (`mc ls`).
- Pipeline retrieves it successfully → extraction stage succeeds.
- `/api/v1/documents/{id}` returns a working signed URL that the mobile app renders.

**Rollback:** flip config back to GCS bucket. Code supports both until the old client is deleted.

**Risks:**
- GCS and S3 have slightly different semantics for signed URLs and object metadata. Validate range requests for large images.

---

### Phase 5 — Auth cutover (Firebase → Authentik)

**Goal:** Backend accepts Authentik-issued OIDC tokens instead of Firebase ID tokens. Mobile and web clients log in via Authentik.

**Scope:**
- Backend: `backend/app/auth/firebase.py`, `dependencies.py`, `middleware.py`, `authorize.py`.
- Web: `web/src/*` auth provider + login screens.
- Mobile: `companion-app/src/auth/*` — deferred to Phase 11.
- Database: `users.email` was the Firebase UID link. Add a new `users.subject` column (OIDC `sub`) nullable at first, backfill for active users, make NOT NULL later.

**Steps:**
1. New module `backend/app/auth/oidc.py`:
   - JWKS fetch + caching from `https://auth.ng20.org/application/o/companion/jwks/`.
   - `verify_oidc_token(token)` → validates signature, audience, issuer; returns claims.
2. `backend/app/auth/dependencies.py` — replace `verify_firebase_token` call with `verify_oidc_token`. Preserve the claim-shape contract (return `{uid, email, ...}`) so call sites don't care.
3. Authentik Application "companion" — PKCE client, redirect URIs for web + mobile (deep link `com.mydailydignity.companion://callback`).
4. Caregiver and admin: Authentik Groups `companion:user`, `companion:caregiver-tier-1`, `companion:caregiver-tier-2`, `companion:caregiver-tier-3`, `companion:admin-viewer`, `companion:admin-editor`, `companion:admin`. Claims mapped into `groups` claim. Backend's tier enforcement reads from there.
5. Users migration: for each Firebase user, create an Authentik user (email match), email them a "set your new password" link. Or prefer: run the flip in a window when user count is small and do it manually.
6. Remove `firebase-admin` from `pyproject.toml`. Delete `auth/firebase.py`.
7. Web: swap Firebase Auth SDK for `oidc-client-ts`. Login page redirects to Authentik.

**Validation:**
- Playwright test: full login loop through Authentik, arrive at the dashboard.
- Existing API tests pass with Authentik-issued test tokens.
- Tier check: a token with `groups=["companion:caregiver-tier-1"]` can read tier-1 resources and fails on tier-2.

**Rollback:** retain Firebase credentials + code on feature flag `COMPANION_AUTH_PROVIDER=firebase|oidc`. Flip back per env.

**Risks:**
- **This is the highest-risk phase.** Touching auth during operation is how outages happen. Do it in staging first, run both providers in parallel for a week (dual-verify middleware — try OIDC first, fall back to Firebase), then retire Firebase.
- Tier mapping: Firebase custom claims → Authentik group claims is a 1:1 mapping but needs care. Write a migration validation Job.

---

### Phase 6 — Voice stack

**Goal:** TTS and STT served from the cluster. Piper for TTS; faster-whisper for STT.

**Steps:**
1. `applications/piper-tts.yaml` + `infra/piper-tts/` — lightweight HTTP wrapper around Piper (there are several community images, e.g., `rhasspy/wyoming-piper`). Service on port 10200. Pre-bake voice profiles matching the four tiers in `docs/architecture.md` §5.6.
2. `applications/faster-whisper.yaml` + `infra/faster-whisper/` — whisper server with GPU off (CPU only; these Macs run the app, Ollama has the GPU). Use `faster-whisper-server` or `openai/whisper-asr-webservice`.
3. Backend: `conversation/tts.py` — replace `google.cloud.texttospeech` client with HTTP POST to the Piper service. Return WAV bytes.
4. Backend: `conversation/stt.py` — replace streaming Google STT with HTTP POST of buffered audio to faster-whisper. *Streaming STT is lost* — reassess if the mobile UX suffers. Alternative: `wyoming-faster-whisper` with its streaming protocol.
5. Voice profile mapping: Piper voices (e.g., `en_US-amy-medium`, `en_US-kusal-medium`) mapped to the four curated profiles. SSML support is limited in Piper — if prosody control matters, evaluate Kokoro as a follow-up.

**Validation:**
- `/api/v1/conversation/tts` returns WAV for a test phrase, <2s for 50 words.
- `/api/v1/conversation/stt` transcribes a known WAV within 20% WER.
- Mobile app plays TTS audio via the existing AVAudioPlayer module.

**Rollback:** provider switch — `COMPANION_TTS_PROVIDER=google` re-activates the Google client (keep it in the tree for rollback until cutover clears).

**Risks:**
- **Streaming STT loss.** Google's streaming STT gives word-by-word transcription; buffered Whisper gives a single transcript after silence. UX feels different. Probably fine for the target user (not an adversarial chatbot), but test.
- **Voice quality.** Piper is good but not Google-WaveNet good. Ship and listen.

---

### Phase 7 — OCR engine

**Goal:** Document AI calls replaced with PaddleOCR (or a VLM via Ollama for high-stakes docs).

**Steps:**
1. `applications/paddleocr.yaml` — PaddleOCR server (e.g., `hjnilsson/paddleocr-api`), CPU-only.
2. Backend: `pipeline/ingestion.py` / wherever Document AI is called — swap to HTTP call to the PaddleOCR service.
3. Evaluate on a fixed test set of 50 bill/legal/medical docs:
   - Recall of key fields (amount, due date, provider name, account number)
   - Layout preservation for tables
4. If PaddleOCR quality is insufficient for a doc class, add a VLM fallback: call Ollama with `qwen2-vl:7b` (or 32b) and a structured prompt. Runs on the existing Ollama stack.

**Validation:**
- On the fixed test set, extraction pipeline achieves >= 85% field-level recall (baseline: measure Document AI on same set first).
- Latency: OCR stage under 5s p50.

**Rollback:** provider switch to Google Document AI (keep the integration code + docai_processor_id config).

**Risks:**
- **This is where local falls furthest behind.** Document AI is specifically tuned for forms, bills, and legal. PaddleOCR is general. The extraction stage may regress noticeably on specific doc types. Have VLM fallback ready.

---

### Phase 8 — Real-time sync + push notifications

**Goal:** Pipeline status updates reach the mobile app in real time without Firestore. Morning check-in and medication reminders still deliver when the app is backgrounded.

**Steps (real-time sync):**
1. Backend: SSE endpoint at `/api/v1/events/stream` — per-user stream of pipeline status updates. Backend publishes to a Redis pub/sub channel `events:user:{user_id}`, the SSE endpoint subscribes and pushes.
2. Mobile: React Native EventSource client.
3. Remove Firestore calls from `events/publisher.py` and pipeline completion hooks.

**Steps (push notifications, pending D3):**

Assuming **D3 = hybrid (APNs direct for iOS, WebSocket-only for Android)**:

1. iOS: backend uses `aioapns` library. Apple Developer cert needed (~$99/yr, already may have). No Firebase in the SDK.
2. Android: no background push. Users only get real-time via SSE when the app is open. Document this as an iOS-first limitation.
3. `services/push_notification_service.py` — swap FCM calls for APNs direct sends.
4. `device_tokens` table — store APNs tokens (iOS) and a "websocket" placeholder (Android). Schema change trivial.

Alternate if **D3 = FCM HTTP v1 direct**:
- Keep using FCM relays but without Firebase SDK. Cross-platform. One Google dependency retained, but scoped to push relay only (no user data in Google's hands).

**Validation:**
- SSE: lock phone, upload a document, unlock → app shows the pipeline update that arrived while backgrounded (only works if the app is still in memory).
- Push: background the app, trigger morning check-in worker, see the push arrive.

**Rollback:** keep Firestore + FCM code behind provider flags.

**Risks:**
- **Android background push.** If D3=hybrid, Android users lose morning check-ins while app is backgrounded. Product impact — needs explicit signoff.
- **APNs certs.** Handling cert renewal is ops burden. Set a calendar reminder.

---

### Phase 9 — Field-level encryption

**Goal:** SSN, bank account, medical record number encrypted with app-managed AES-256-GCM instead of Cloud KMS.

**Steps:**
1. `backend/app/services/kms_service.py` — replace `google.cloud.kms` calls with `cryptography.aead.AESGCM`.
2. Key in a SealedSecret: `COMPANION_FIELD_ENCRYPTION_KEY` (32 bytes, base64). Generate once: `openssl rand -base64 32`.
3. Rotate: derive per-envelope nonce from `secrets.token_bytes(12)`, store nonce alongside ciphertext in the column (bytes || nonce || ciphertext || tag — fixed layout).
4. Migration: existing KMS-encrypted fields need re-encryption. Write a one-shot Job that reads every row, decrypts via KMS (last Google dependency), re-encrypts locally, writes back.

**Validation:**
- Roundtrip encrypt/decrypt per field type in unit tests.
- Migration Job: reencryption completes for all rows, no decrypt errors on subsequent reads.

**Rollback:** unsupported after migration. Don't migrate until you're committed. Keep KMS key in GCP for 90 days after cutover in case recovery is needed.

**Risks:**
- **Key loss = data loss.** The sealed secret must be backed up out-of-cluster (e.g., encrypted in 1Password or a personal vault). If the cluster is destroyed, you need this key to decrypt backups.
- Rotation strategy: add a `key_version` byte to the layout so new keys can coexist with old ones.

---

### Phase 10 — Observability + backups

**Goal:** Logs from all tenants aggregated in Loki. Metrics in Prometheus. Dashboards in Grafana at `grafana.ng20.org`, OIDC-authed via Authentik. Backups to an offsite destination.

Like Authentik and MinIO, the observability stack is shared infrastructure — serves Companion, Silkstrand, and homelab workloads. Per-tenant scoping via Grafana Organizations or folder-level permissions; tenant roles map to Authentik Groups (`infra:viewer`, `infra:editor`, `infra:admin`, `companion:ops`, etc.).

**Steps:**
1. `applications/prometheus.yaml` — kube-prometheus-stack Helm chart in `observability` namespace.
2. `applications/loki.yaml` — Loki in single-binary mode, **backed by MinIO** (uses the `loki-storage` bucket + a dedicated `loki` IAM user — pattern matches companion-backend).
3. `applications/promtail.yaml` — Promtail DaemonSet for log shipping.
4. Grafana ships inside kube-prometheus-stack. Configure:
   - Traefik `IngressRoute` on `grafana.ng20.org`
   - OIDC auth against Authentik (`grafana` Application in Authentik, client_id + secret as SealedSecret)
   - Role mapping: `infra:admin` → Grafana Admin, `infra:editor` → Editor, `infra:viewer` → Viewer
5. Dashboards: import CNPG dashboard, MinIO dashboard, Traefik dashboard, Longhorn dashboard, plus a custom Companion dashboard (request rate, p50/p99 latency, pipeline stage durations, auth errors).
6. Backend: replace `PIIMaskingFilter` target. It currently formats for Cloud Logging; refactor to emit structured JSON to stdout with same masking rules — Promtail ingests it.
7. Alerting: email to you via the mail-relay on critical alerts (pipeline failure rate > 10%, Postgres replication lag > 60s, Ollama endpoint down, Longhorn replica degraded).
8. Backups:
   - CNPG `ScheduledBackup` → MinIO (already Phase 2), using `cnpg-backup` user.
   - Nightly `restic` Job → offsite (D10 destination). Targets: MinIO buckets `companion-documents`, `companion-archives`, `silkstrand-*`, and Postgres base backups. Uses the `restic-offsite` IAM user.
   - MinIO S3 API at `s3.ng20.org` enabled here (via Traefik `IngressRoute` + Tunnel) so the offsite restic job (running on the NAS or another machine) can push directly.

**Validation:**
- Grafana shows companion pod logs with fields masked.
- Force a pipeline failure; alert arrives in email within 2 min.
- Delete a random MinIO object, restore from restic snapshot.

**Rollback:** low-stakes; delete Applications.

---

### Phase 11 — Mobile app rebuild

**Goal:** React Native app authenticates through Authentik, handles pushes per D3, and talks to the new backend URL.

**Steps:**
1. Swap `@react-native-firebase/auth` for a generic OIDC client (`react-native-app-auth`).
2. Configure OIDC client with Authentik issuer + client ID + PKCE + redirect URI (`com.mydailydignity.companion://callback`).
3. `src/auth/AuthProvider.tsx` — rewrite to use `react-native-app-auth` tokens. Token storage: Keychain (iOS) / EncryptedSharedPreferences (Android).
4. `src/notifications/` — per D3 implementation.
5. `src/api/client.ts` — point at `api.mydailydignity.com`. Pass OIDC access token in `Authorization: Bearer`.
6. Remove `@react-native-firebase/*` packages from `package.json`.
7. Deep link scheme registration: iOS Info.plist, Android AndroidManifest.xml.

**Validation:**
- iOS + Android builds both pass.
- Full auth flow works: local account + Google via Authentik.
- Push delivery works per D3 expectations.

**Rollback:** not really — keep the Firebase-auth build as an archived release for the cutover window.

**Risks:**
- **Existing users need to re-login.** Plan a release-notes note.
- iOS deep link collision if any other app claims the scheme — use a reverse-DNS bundle prefix.

---

### Phase 12 — Cutover & teardown

**Goal:** Production traffic on self-hosted. GCP resources deleted.

**Steps:**
1. Deploy `companion-prod` Application. Run in parallel with GCP-hosted prod for 2 weeks, reading the same Postgres (via VPN tunnel back to Cloud SQL) — OR better, freeze prod, dump, restore into CNPG, flip DNS.
2. DNS flip: `api.mydailydignity.com` → Traefik (via Tunnel). Monitor for 48h.
3. Mobile clients pick up new API URL via a staged release.
4. GCP teardown — use existing destroy workflow in `.github/workflows/destroy.yml`. Execute in order:
   - Cloud Run services
   - Pub/Sub subscriptions & topics
   - Cloud Scheduler jobs
   - Cloud Storage buckets (after backup)
   - Cloud SQL (after final dump)
   - Memorystore
   - Secret Manager secrets
   - KMS keys — **only after the 90-day safety window**
   - VPC + networking last
5. Firebase project: disable Auth, FCM, Firestore. Keep the project shell for 30 days as a rollback hedge.

**Validation:**
- 7 days of clean prod metrics on self-hosted.
- Backup restore drill executed successfully in staging.

**Rollback:** DNS flip back to GCP — possible only for 48h after cutover (Cloud SQL writes diverge after that). Past 48h, rollback means restoring from self-hosted backups into GCP — an order of magnitude harder. Design the cutover window with that in mind.

**Risks:**
- **This is the "no going back" moment.** Over-test the rollback drill before attempting.
- User re-authentication at cutover is unavoidable if the OIDC flip happens at the same time. Consider staggering: Phase 5 can ship before Phase 12 (backend dual-verifies both providers for a week).

---

## 6. Decisions log

### Decided
- **Migrate, not rebuild.** Domain logic is vendor-neutral; swaps happen at the edges.
- **Single gitops repo:** `~/repo/argocd-apps` (the earlier `companion-gitops` scaffold was deleted).
- **Architecture tier split:**
  - Macs = Ollama-only, bare metal. No K8s on them in the target state.
  - K8s cluster = 3 Minisforum AI X1-255 nodes (Ryzen 7 255, 64GB, dual NVMe, 2.5GbE).
- **K3s in HA mode** with 3 control plane nodes, embedded etcd.
- **Storage: Longhorn, 3-replica, one replica per node.** Replaces the earlier "local-path + nfs-client" split and supersedes the Ceph consideration. NAS demoted to bulk/backup target.
- **Object storage:** MinIO single-pod on a Longhorn-backed PVC (was NFS-client).
- **Primary DB:** CNPG 3-instance clusters on Longhorn volumes, with CNPG streaming replication layered on top of Longhorn's block replication.
- **Authentik as shared-infrastructure IDP.** Local accounts + Google OIDC upstream. PKCE flow for mobile. Serves Companion (mydailydignity.com), Silkstrand (silkstrand.io), and ng20.org homelab tools. Hosted at `auth.ng20.org`.
- **Authentik DB on CNPG** (D5 closed — consistency over expedience).
- **Shared-infrastructure domain convention:** `ng20.org` hosts tools (Argo CD, Authentik, Zot, MinIO console, Grafana). Product domains (`mydailydignity.com`, `silkstrand.io`) host only product surfaces. Group naming in Authentik: `<tenant>:<role>`.
- **MinIO as shared object store.** One deployment, multiple tenants via per-tenant IAM users (`companion-backend`, `cnpg-backup`, `restic-offsite`, `silkstrand-*`). Root credentials are break-glass only. In-cluster consumption via ClusterIP; console at `s3-console.ng20.org` (Authentik OIDC); S3 API optionally exposed at `s3.ng20.org` for off-cluster callers.
- **Grafana at `grafana.ng20.org` with Authentik OIDC** (Phase 10). Observability stack shared across tenants.
- **Zot at `zot.ng20.org`** — already deployed, will be OIDC-integrated with Authentik in the Phase 1 follow-up pass.
- **Argo CD at `argocd.ng20.org`** — already deployed, will drop its default admin password once Authentik OIDC is wired up in Phase 1 follow-up.
- **Firestore → Redis pub/sub + SSE** for real-time pipeline status (D7 closed).
- **Mobile reachability:** existing Cloudflare Tunnel on `*.mydailydignity.com` (D6 closed).
- **Intra-cluster TLS:** plain HTTP. Cloudflare Tunnel terminates at the edge (D8 closed).
- **Observability:** kube-prometheus-stack + Loki + Promtail (D9 closed).
- **Email verification** uses the existing in-cluster SMTP relay.
- **Events:** in-process direct calls (no Pub/Sub replacement needed).
- **Field encryption:** app-level AES-256-GCM, key in SealedSecret.
- **Ollama deployment:** bare-metal launchd LaunchDaemon on each Mac, bound to `0.0.0.0:11434`, `KV_CACHE_TYPE=q8_0`, `FLASH_ATTENTION=1`. Already running on both Macs.
- **Model placement:** primary LLM (D1) on studio-ultra, embeddings (D2) on studio-max.

### Open (see §4 for details)
- D1: Primary LLM model — **recommended Qwen 2.5 32B**
- D2: Embedding model — **recommended bge-m3 (1024-dim)**
- D3: Push notifications strategy — **recommended hybrid APNs-direct + WebSocket**
- D4: OCR engine — **recommended PaddleOCR first, VLM fallback**
- D10: Offsite backup destination

### Rejected
- **Rebuild from scratch** — the pipeline, safety layer, and caregiver model are too expensive to re-derive.
- **Single-repo `companion-gitops`** — `argocd-apps` already exists and drives the cluster.
- **Ceph for 3-node home cluster** — operational complexity vs benefit ratio wrong at this scale; Longhorn is the right-sized tool. (Would reconsider at ~10+ nodes or if we needed CephFS.)
- **Running K8s on the Mac Studios (OrbStack K3s)** — OrbStack virtualization costs real perf (no Metal GPU for pods), added NFS/storage-provisioner problems, and conflated inference + compute tiers. Separation wins.
- **4 OrbStack VMs across 2 Macs** — same 2-physical-failure-domains, much higher ops cost, OrbStack tax doesn't disappear.
- **NFS-backed MinIO** — moved to Longhorn for HA and reduced NAS dependency. NAS still used for media and offsite backup.
- **Keeping Firebase Auth** — user wants full independence; hybrid complicates mobile auth.
- **Vault Transit for field encryption** — overkill for a home cluster.

---

## 7. Appendix

### A. GCP API touchpoints in backend/app

Files that import from `google.*` or `firebase_admin`:

```
backend/app/api/v1/conversation.py
backend/app/conversation/llm.py          (Phase 3)
backend/app/conversation/tools.py        (Phase 3)
backend/app/auth/firebase.py             (Phase 5, delete)
backend/app/services/push_notification_service.py   (Phase 8)
backend/app/pipeline/ingestion.py        (Phase 4)
backend/app/api/v1/documents.py          (Phase 4)
backend/app/services/image_analysis_service.py (Phase 4)
backend/app/pipeline/events.py           (Phase 8)
backend/app/services/kms_service.py      (Phase 9)
backend/app/api/admin/seed_admin.py      (review)
backend/app/pipeline/embeddings.py       (Phase 3)
backend/app/conversation/retrieval.py    (Phase 3 — uses embeddings)
backend/app/services/account_lifecycle_service.py (Phase 4 + Phase 5)
backend/app/notifications/channels.py    (Phase 8)
backend/app/conversation/tts.py          (Phase 6)
backend/app/conversation/stt.py          (Phase 6)
backend/app/events/publisher.py          (Phase 8)
```

### B. Firebase SDK touchpoints in mobile app

```
companion-app/package.json                          (dependency removal)
companion-app/ios/CompanionApp.xcodeproj/project.pbxproj   (Pod cleanup)
companion-app/ios/Podfile.lock                      (Pod cleanup)
companion-app/src/auth/AuthProvider.tsx             (rewrite)
companion-app/src/auth/LoginScreen.tsx              (rewrite)
companion-app/src/auth/VerifyEmailScreen.tsx        (rewrite or delete)
companion-app/src/hooks/usePushNotifications.ts     (rewrite)
companion-app/src/notifications/backgroundHandler.ts (rewrite)
companion-app/src/api/client.ts                     (URL + token changes)
companion-app/src/screens/TodayScreen.tsx           (Firebase call sites)
companion-app/src/components/ScanButton.tsx         (Firebase call sites)
companion-app/src/hooks/useImageAnalysis.ts         (Firebase call sites)
```

### C. GCP teardown order

After Phase 12 validation:
1. Cloud Run services
2. Cloud Scheduler jobs (no longer invoking)
3. Pub/Sub subscriptions, then topics
4. Cloud Storage (after last sync to MinIO)
5. Cloud SQL (after final pg_dump archived in MinIO)
6. Memorystore
7. Secret Manager secrets
8. Firebase Cloud Messaging configuration
9. Firebase Auth tenants (after re-authentication is proven)
10. Firestore (after SSE is proven)
11. Cloud KMS keys — **90-day safety window**
12. VPC + service networking + WIF (last)

### D. What remains externally dependent

- **Apple APNs relay** for iOS background push — cannot be self-hosted. No user PII transits.
- **Google FCM relay** (if D3=FCM-direct) — same as APNs. Optional per D3.
- **Google OIDC** as an upstream IdP option — optional; local accounts also available.
- **Cloudflare** for DNS + tunnel — public reachability.
- **GitHub** for source + CI — could move to self-hosted Forgejo/Gitea later if desired; not in this plan.
- **Apple Developer Program** cert — iOS app signing; not self-hostable.

---

*Last updated: 2026-04-19*
