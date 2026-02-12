# Data retention and production database policy

This document describes how customer data is protected in the SecureAI Guardian deepfake detection stack. **Nothing is automatically deleted from production databases by default.**

---

## Summary

| Data | Auto-deleted? | When / how |
|------|----------------|------------|
| **Analyses** (scan results, verdicts, proofs) | **No** | Never, unless you explicitly enable retention (see below). |
| **Device identities** (node IDs, scan history, audit history) | **No** | No code path deletes these. |
| **Result JSON files** (in `results/` or `results_data` volume) | **No** | No scheduled deletion. |
| **Postgres / volumes** | Only if you run `docker compose down -v` | **Do not use `-v`** if you want to keep data. |

---

## Production safeguards

### 1. No automatic deletion of analyses

- The **Flask API** (`api.py`) does **not** delete any `Analysis` or `DeviceIdentity` rows.
- The **Celery** task `cleanup_expired_results` calls `cleanup_old_records()`, but that function **deletes nothing** unless you set **`DATA_RETENTION_DAYS`** in the environment (see [Opt-in retention](#opt-in-retention)).
- So by default, all analyses stay in the database for the life of the deployment.

### 2. User → analyses relationship

- In `database/models.py`, the `User` → `analyses` relationship uses **`cascade="save-update"`** only (no `delete` or `delete-orphan`).
- Deleting a user does **not** delete their analyses. Analyses remain in the DB.

### 3. Device identities and scan history

- **Device identities** and their **scan_history** / **audit_history** JSON are only ever **read** and **updated** by the API (sync, login, scan count). There is **no endpoint or task** that deletes device identities or clears history.

### 4. Result files

- Result JSONs are written to the **results** folder (or `results_data` named volume in Docker). There is **no scheduled job** that deletes these files. They persist until you remove them manually or wipe the volume.

---

## Opt-in retention (optional)

If you want to **automatically** remove old analyses (e.g. for compliance or storage limits), you must **opt in**:

1. Set the environment variable **`DATA_RETENTION_DAYS`** to a positive number (e.g. `365` for one year).
2. Only then will **`cleanup_old_records()`** (used by the Celery task `cleanup_expired_results`) actually delete analyses older than that many days.
3. If `DATA_RETENTION_DAYS` is **not set**, or is `0` / `off` / `never`, the function returns without deleting anything.

**Example (Docker):**

```yaml
# In docker-compose or .env, only if you want automatic deletion:
environment:
  - DATA_RETENTION_DAYS=365
```

**Recommendation for customers:** Leave `DATA_RETENTION_DAYS` **unset** unless you have a clear retention policy. Default behavior is **never delete**.

---

## Keeping data across redeploys

- Use **named volumes** for Postgres (`postgres_data`) and results (`results_data`) as in the project’s Docker Compose files.
- When stopping or rebuilding, use **`docker compose down`** **without** the **`-v`** flag. Using **`docker compose down -v`** removes volumes and **permanently deletes** all DB and result data.

See **COPY_PASTE_COMMANDS.md** (section 9) for exact commands.

---

## Tables used by the production API

| Table | Purpose | Deleted by app? |
|------|---------|------------------|
| `analyses` | One row per video scan (verdict, confidence, blockchain_tx, etc.) | No (unless opt-in retention) |
| `device_identities` | Device fingerprint, node_id, alias, tier, scan_history, audit_history | No |
| `users` | Legacy auth (optional); Guardian uses device_identities | No (and no cascade delete of analyses) |

---

## For customer deployments

When selling or deploying to customers:

1. **Do not** set `DATA_RETENTION_DAYS` unless they require automatic retention.
2. **Do not** run `docker compose down -v` on production.
3. Back up **Postgres** (e.g. `pg_dump`) and the **results** volume or folder regularly if they need auditability or disaster recovery.
4. The API and Celery code paths are designed so that **analyses and device data are not deleted** unless you explicitly enable retention.
