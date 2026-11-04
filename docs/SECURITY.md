# Security Architecture & Hardening Guide
## Local-First Automated PRD Engineering Framework

**Status:** Implemented & Verified  
**Version:** 1.0.0

---

## 1. Security Architecture Principles

1. **Zero Cloud Egress:** All AI inferences, telemetry, and database queries are restricted to the local host (`localhost` / private network).
2. **Data Sovereignty:** Uploaded reference files and exported documents reside in segregated local directories (`/data/uploads`, `/data/exports`).
3. **Explicit Authentication:** Implicit development sessions are disabled by default in production.

---

## 2. Implemented Security Controls

### 2.1 File Upload Defense
- **Maximum File Size:** Enforced at 15 MB (`MAX_UPLOAD_SIZE_BYTES = 15728640`). Payloads exceeding this threshold are rejected with HTTP 413.
- **Extension Allowlist:** Restricted to `.pdf`, `.txt`, `.md`, and `.docx`. All other extensions return HTTP 400.
- **MIME Type Allowlist:** Restricted to `application/pdf`, `text/plain`, `text/markdown`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- **Executable Disguise Inspection:** Magic byte checking rejects files beginning with Windows PE headers (`MZ`) or Linux ELF headers (`\x7fELF`), preventing renamed executables from reaching disk.
- **Path Traversal Protection:**
  - Filename extraction takes strictly `Path(filename).name`.
  - Base filenames are sanitized using regex `[^\w\.-]` to eliminate path manipulation characters (`..`, `/`, `\`).
  - Destinations are generated using UUID prefixes (`{project_id}_{uuid}_{sanitized_basename}`).
  - Destination resolution is asserted against `UPLOADS_DIR.resolve()`.

### 2.2 Database Integrity & Index Constraints
- **Unique Indexes:** Enforced at the MongoDB engine level on `users.username` (`uniq_username`) and `users.email` (`uniq_email`).
- **Idempotent Initialization:** `backend/app/db/indexes.py` aggregates and eliminates duplicate records prior to index creation, preventing startup crashes.
- **Version Uniqueness:** `prd_versions` enforces a compound unique index on `(prd_id, version_number)`.

### 2.3 Authentication & Authorization
- **Password Hashing:** Passwords are salted and hashed using direct `bcrypt.hashpw` with per-user unique salts. Truncated to 72 bytes to respect bcrypt specifications.
- **JWT Cryptography:** Signed using `PyJWT` with `HS256` and configurable expiration (default 7 days).
- **Production Guard:** `ALLOW_DEV_AUTO_AUTH` defaults to `False`. When `False`, any request lacking a valid `Authorization: Bearer <token>` header is rejected with HTTP 401 Unauthorized.

---

## 3. Automated Security Verification

The automated security regression test suite `backend/tests/test_security.py` tests:
- `test_security_auth_rejection`: Confirms unauthenticated requests without tokens receive 401.
- `test_security_upload_restrictions`:
  - 16 MB upload rejected with HTTP 413.
  - `.exe` extension rejected with HTTP 400.
  - `MZ` executable header disguise rejected with HTTP 400.
  - Empty files rejected with HTTP 400.
  - `../../etc/passwd.txt` path traversal sanitized safely.
- `test_security_duplicate_username_enforcement`: Confirms duplicate registrations are rejected with HTTP 400.

