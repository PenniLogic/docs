# PenniLogic — Development Environment & Tooling

> **Status:** Verified and provisioned on this machine, 2026-09-01.
> This documents what is **actually installed and tested**, not what is theoretically recommended.

---

## 1. Verified local toolchain

| Tool | Version / Path | Status |
|---|---|---|
| **JDK** | OpenJDK 21.0.12.1 LTS (Microsoft) | ✅ Correct LTS for modern Android/Gradle |
| **Gradle** | 9.7.1 (bundled Kotlin 2.4.0) | ✅ Current |
| **Android SDK** | `%LOCALAPPDATA%\Android\Sdk` | ✅ |
| — build-tools | 36.0.0, 36.1.0, **37.0.0** | ✅ |
| — platforms | android-36, **android-37.0** | ✅ Can target latest |
| — system images | android-36 (Play Store), **android-31 (Google APIs)** | ✅ Both sides of the Android 12 boundary |
| — AVDs | `Pixel_8_API36`, `Pixel_5_API31` | ✅ |
| **adb** | `platform-tools\adb.exe` | ✅ |
| **Node.js / npm / pnpm** | Program Files\nodejs | ✅ For web + admin |
| **bun** | `~\.bun\bin\bun.exe` | ✅ Optional fast runner |
| **Python** | 3.14 | ✅ For the AI service |
| **uv** | available | ✅ Recommended Python package manager |
| **Docker** | Docker Desktop | ✅ Running Postgres + Redis (§3) |
| **git / gh** | available | ✅ Repo initialised (§4) |
| Go | ❌ missing | Not needed — stack is Kotlin/Python/TS |
| kotlinc (standalone) | ❌ missing | Not needed — Gradle supplies the compiler |

### Why two AVDs

`Pixel_8_API36` targets the current platform. **`Pixel_5_API31` exists specifically to test the
Android 12 "restricted settings" boundary**, which changes how `NotificationListenerService` access
can be granted for apps installed outside the Play Store. Since notification capture is now a
co-primary ingestion channel (see the feasibility doc), this behaviour must be verified on both
sides of that boundary rather than assumed.

> ⚠️ **The `sdkmanager` CLI is deprecated** on this SDK version and mis-parses the classic
> `system-images;android-31;...` semicolon syntax, failing with a confusing
> "Package system-images not found". Use the new `android` CLI with **slash** paths:
> ```
> android.exe sdk install "system-images/android-31/google_apis/x86_64"
> android.exe sdk list --all "system-images/android-31/*"
> ```

---

## 2. MCP connectors

### Installed and verified

| Connector | Status | Purpose |
|---|---|---|
| **Context7** | ✅ **Installed & handshake-tested** (v4.0.4) | Current, version-accurate library docs. High value because Compose / Gradle / Play Billing APIs move faster than model training data. |

Added to `~\.copilot\mcp-config.json`. The existing config was backed up first, and the GitHub token
was verified byte-identical after the edit (SHA-compared, not eyeballed — the display masks secrets).

> Note: `npx`-based MCP servers on this machine require
> `NODE_EXTRA_CA_CERTS=C:\Users\ttbasil\Documents\zscaler-ca-bundle.pem` due to TLS interception.
> This is set on the Context7 entry, matching the existing Playwright entry.

### Already available

| Connector | Use for PenniLogic |
|---|---|
| **mobile-canvas** | Boot/control emulators, install APKs, drive UI, read logcat, inspect accessibility tree. Directly useful for testing SMS/notification ingestion. |
| **playwright** | E2E testing of web app and admin console. |
| **github** | Repo, issues, PRs, code search. |
| **figma** | Design handoff → code, design tokens. |
| **agent-council** | Multi-perspective review gate for high-stakes artifacts. |

### Deliberately *not* installed (require credentials that don't exist yet)

Installing these now would only create broken config entries:

| Connector | Blocked on | Install when |
|---|---|---|
| Postgres MCP | Would point at a schema we haven't designed | Schema work begins. **Dev DB only, never production.** |
| Stripe MCP | Needs API keys | Billing work begins. **Test-mode keys only.** |
| Sentry MCP | Needs a Sentry org/project | Observability setup |

### Recommended skills

- [PostgreSQL Optimization](https://github.com/github/awesome-copilot/blob/main/skills/postgresql-optimization/SKILL.md)
- [Stripe Best Practices](https://github.com/stripe/ai/blob/main/skills/stripe-best-practices/SKILL.md)
- Already installed and worth using deliberately: **`impeccable`** / **`premium-frontend-ui`** for the
  web and admin UI (a finance product lives on trust, and polish is a trust signal), and
  **`agent-council`** for reviewing the PRD and security design.

---

## 3. Local services (running)

`docker-compose.yml` at the repo root provisions:

| Service | Version | Port | Purpose |
|---|---|---|---|
| **Postgres** | 17.11-alpine | 5432 | Primary datastore, double-entry ledger |
| **Redis** | 7-alpine | 6379 | AI quota token buckets, prompt caching |

```powershell
docker compose up -d       # start
docker compose ps          # both should report (healthy)
docker compose down        # stop, keep data
docker compose down -v     # stop and DESTROY data
```

Both verified healthy. Postgres is initialised with `--locale=C` so ordering is deterministic across
dev machines and CI. Redis runs with `appendonly yes` so quota counters survive restarts — otherwise
testing daily/monthly quota windows silently resets.

**A live demonstration of ADR-001**, run against this Postgres instance:

```
float:        0.1 + 0.2  =  0.30000000000000004
minor units:   10 +  20  =  30
```

This is why money is stored as integer minor units and never as a float.

> Credentials in the compose file are local-development only and deliberately non-secret. Real
> credentials belong in a secrets manager — see the security architecture doc.

---

## 4. Version control

The folder was **not** under version control. `git init` has been run (default branch `main`) and the
full research phase is committed.

`.gitignore` covers secrets (`.env`, `*.pem`, `*.jks`, `*.keystore`, `google-services.json`,
`service-account*.json`), Android/Gradle build output, Node, Python, IDE and OS noise, and
**on-device ML model binaries** (`*.task`, `*.tflite`, `*.onnx`) which should be fetched at build
time rather than committed.

No remote is configured yet — add one when the GitHub repo exists.

---

## 5. Security rules for tooling

Non-negotiable, given what this app handles:

1. **No production data in any MCP connector.** Database connectors point at local/dev only.
2. **Test-mode keys only** for billing connectors in development.
3. **No secrets in the repo.** Secret scanning in CI from day one.
4. **Vet every dependency and SDK.** Play policy forbids any transfer resulting in sale of
   SMS-derived data — *including via third-party SDKs*. Ad/analytics SDKs are effectively banned from
   the Android app. Enforce with a CI dependency allowlist, not a convention.
5. **Pin and review MCP servers** like application dependencies.

---

## 6. Remaining gaps

| Gap | Impact | Notes |
|---|---|---|
| **Physical Android device with an Indian SIM** | **High** | Real bank SMS formats, sender IDs (`VM-HDFCBK`, `AD-ICICIB`) and payment-app notifications **cannot be emulated**. The parser is the core of the product and needs real inputs. This is the most important outstanding item. |
| Android Studio | Medium | Not verified from CLI. Needed for layout inspector, profiler, AVD management. |
| Git remote | Low | Add when the GitHub repo is created. |
