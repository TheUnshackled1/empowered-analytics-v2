# 🏛️ CHED Status 4 — System Integration Strategy Report

> **Project Title:** **OAS — Outcomes Assessment & Accreditation System (`EmpowerED API v2.0`)**  
> **Submitted To:** **Prof. Jose Leo G. Redoblo**  
> **Proponent / Lead Developer:** **John Tyrone Pagunsan Coronel** ([`TheUnshackled1`](https://github.com/TheUnshackled1))  
> **Institution:** **Carlos Hilado Memorial State University (CHMSU) / Technological Institute of the Philippines (T.I.P.)**  
> **Deliverable:** **CHED Status 4 (100 Points | Due Nov 26, 8:30 AM) — Integration Strategy (`OAS.pdf`)**  
> **Official Letterhead PDF Deliverable:** [`OAS.pdf`](OAS.pdf)

[![Official PDF Deliverable](https://img.shields.io/badge/📄_Official_CHMSU_Letterhead_PDF-OAS.pdf-16a34a?style=flat-square)](OAS.pdf)
[![LMS Integration](https://img.shields.io/badge/1._LMS_Webhook-Canvas_LTI_1.3_REST_API-0ea5e9?style=flat-square)](#2-inbound-lms-integration--canvas-lti-13-webhook--etl-pipeline)
[![SSO & IAM](https://img.shields.io/badge/2._Identity_&_SSO-Microsoft_OAuth_2.0_%2B_15m_Session-6366f1?style=flat-square)](#3-identity--access-management-iam--sso-integration)
[![SIS & Legacy DB](https://img.shields.io/badge/3._Database_&_SIS-SQLite_3_%2B_PostgreSQL_17_Adapter-10b981?style=flat-square)](#4-legacy-sis-database--curriculum-erp-synchronization)
[![Accreditation Export](https://img.shields.io/badge/4._Accreditation_ERP-FPDF2_SSR_%2B_RA_10173_Print_Seal-f59e0b?style=flat-square)](#5-outbound-accreditation--erp-reporting-integration)

---

## 📋 Submission Metadata & Deliverable Scope

| Field | Details |
|---|---|
| **Assignment / Milestone** | **CHED Status 4 — Integration Strategy** (100 Points · Due Nov 26, 8:30 AM · `- OAS`) |
| **Requirement** | *Explains how the new system connects with existing tools (e.g., ERP, CRM, LMS, identity providers, or legacy databases) via APIs or middleware* |
| **Instructor** | **Prof. Jose Leo G. Redoblo** |
| **Primary PDF Submission** | **[`OAS.pdf`](OAS.pdf)** (Compiled directly onto the official **Carlos Hilado Memorial State University** letterhead preserving the original header and **"GREEN CHMSU ExCELSIOR!"** footer on every page) |
| **Codebase Architecture** | **10 REST API v2 Middleware Endpoints** ([`analytics/urls.py`](analytics/urls.py), [`analytics/views.py`](analytics/views.py)), **8 DRF Payload Serializers** ([`analytics/serializers.py`](analytics/serializers.py)), **Dual-Engine ORM Database Adapter** ([`empowered_project/settings.py`](empowered_project/settings.py)), and **RA 10173 SHA-256 Privacy & Audit Guard** ([`analytics/models.py`](analytics/models.py)) |

---

## 1. Executive Integration Architecture Overview

Modern higher education institutions operate heterogeneous software ecosystems: faculty grade student work inside a **Learning Management System (Canvas LMS)**, user identities reside in an **Institutional Single Sign-On Directory (Microsoft OAuth 2.0 / Active Directory)**, course catalogs and historical records reside in **Legacy & Relational Student Information System (SIS) Databases (SQLite 3 / PostgreSQL 17)**, and Quality Assurance (QA) committees require standardized **CHED OBE & ABET Self-Study Report (SSR) exports**.

Rather than forcing faculty to export CSV/Excel files from Canvas and manually re-encode them into accreditation spreadsheets, **OAS (`EmpowerED API v2.0`)** acts as a centralized **REST API v2 Integration Middleware** that connects all four external and internal tools through authenticated webhooks, DRF serializers, and ACID database adapters:

```mermaid
flowchart LR
    subgraph ExternalSystems["Existing Institutional Tools & External Platforms"]
        LMS["1. Canvas LMS<br/>(LTI 1.3 Rubric Engine)"]
        IDP["2. Institutional Identity / SSO<br/>(Microsoft OAuth 2.0 + 2FA)"]
        SIS[("3. Legacy & Production SIS DB<br/>(SQLite 3 / PostgreSQL 17)")]
        ERP["4. Quality Assurance & CHED/ABET<br/>Accreditation Portals"]
    end

    subgraph Middleware["OAS / EmpowerED API v2.0 Integration Middleware (Tip-API)"]
        WH["POST /api/v2/hooks/canvas-sync/<br/>Bearer Key Auth + DRF Serializer"]
        AUTH["POST /api/v2/auth/session-login/<br/>POST /api/v2/auth/sso/<br/>900s Sliding Cookie + RBAC L1-L3"]
        ETL["RA 10173 SHA-256 Tokenization<br/>+ Atomic ORM Adapter (conn_max_age=600)"]
        STATE["GET /api/v2/dashboard/state/<br/>PATCH /api/v2/matrix/mapping/<br/>PATCH /api/v2/abet/criteria/"]
        EXP["POST /api/v2/reports/abet-ssr/<br/>POST /api/v2/reports/abet-print-seal/"]
    end

    LMS -->|"LTI 1.3 JSON Webhook<br/>Authorization: Bearer tip_live_..."| WH
    IDP <-->|"OAuth 2.0 Handshake<br/>tip_oauth_<24_hex> Token"| AUTH
    WH --> ETL
    AUTH --> ETL
    ETL <-->|"dj-database-url & psycopg 3.3<br/>ACID transaction.atomic()"| SIS
    SIS --> STATE
    STATE --> EXP
    EXP -->|"Binary A4 PDF Stream (%PDF-1.4)<br/>+ X-Audit-Hash Seal"| ERP
```

### Master External & Legacy System Integration Matrix

| Connected Tool / Legacy System | Integration Pattern & Protocol | Exact Codebase Endpoint & Handler | Payload Validation & Adapter | Security & RA 10173 DPA Mechanism |
|---|---|---|---|---|
| **1. Canvas LMS (LTI 1.3 Rubric & Gradebook Engine)** | Inbound Event-Driven REST Webhook (`HTTP POST` JSON) | `POST /api/v2/hooks/canvas-sync/` → [`CanvasSyncWebhookAPIView`](analytics/views.py#L318-L393) | [`CanvasWebhookIngestSerializer`](analytics/serializers.py#L40-L53) validates `course_code`, `canvas_rubric_id`, `student_number`, and 5-domain `scores` | Constant-time Bearer token check (`secrets.compare_digest`), SHA-256 student ID hashing (`hashlib.sha256`), and `SYNC · Canvas` audit hash |
| **2. Institutional Identity Provider (Microsoft OAuth 2.0 / SSO & Directory)** | REST Authentication & Token Exchange (`HTTP POST` JSON + `HttpOnly` Cookie) | `POST /api/v2/auth/session-login/` → [`EmpowerEdSessionLoginAPIView`](analytics/views.py#L492-L558)<br/>`POST /api/v2/auth/sso/` → [`InstitutionalSSOAPIView`](analytics/views.py#L437-L489) | [`InstitutionalSSOSerializer`](analytics/serializers.py#L34-L37) & `InstitutionalUser.check_password()` | Issues per-login `tip_oauth_<24_hex>` token, masks client display, stores only SHA-256 token digest in `DPAAuditLog` (`AUTH · OAuth`), sets 900s sliding cookie |
| **3. Legacy & Production SIS / Curriculum Databases (SQLite 3 & PostgreSQL 17)** | 12-Factor Dual-Engine ORM Adapter (`dj-database-url` + `psycopg[binary]` 3.3) | [`empowered_project/settings.py`](empowered_project/settings.py#L67-L78), `GET /api/v2/dashboard/state/`, `PATCH /api/v2/matrix/mapping/` | [`CourseMatrixSerializer`](analytics/serializers.py#L19-L31), [`MatrixCellUpdateSerializer`](analytics/serializers.py#L56-L61), `dj_database_url.config(conn_max_age=600)` | `transaction.atomic()` ACID guarantees, RBAC Level `>= 2` write guard, and `WRITE · SO Map` SHA-256 audit logging |
| **4. CHED OBE & ABET Accreditation Reporting / ERP Consumers** | Outbound Binary PDF Stream (`application/pdf`) & Cryptographically Sealed Print View | `POST /api/v2/reports/abet-ssr/` → [`ABETReportExportAPIView`](analytics/views.py#L667-L694)<br/>`POST /api/v2/reports/abet-print-seal/` → [`ABETPrintSealAPIView`](analytics/views.py#L652-L664) | [`ABETReportExportSerializer`](analytics/serializers.py#L71-L78) & [`build_abet_ssr_pdf()`](analytics/services.py#L307-L455) (`fpdf2` in-memory `BytesIO`) | Embeds `X-Audit-Hash` & `X-Audit-Timestamp` HTTP headers and verifies `EXPORT · PDF` / `EXPORT · Print` seals against `DPAAuditLog` |
| **5. API Security & Alert Management Gateway** | REST Configuration & Live Key Rotation (`HTTP PATCH` / `HTTP POST`) | `POST /api/v2/config/rotate-key/` → [`RotateAPIKeyAPIView`](analytics/views.py#L697-L734)<br/>`PATCH /api/v2/config/settings/` → [`MiddlewareConfigAPIView`](analytics/views.py#L737-L806) | [`MiddlewareConfigSerializer`](analytics/serializers.py#L81-L91) & singleton [`MiddlewareConfig.load()`](analytics/models.py#L131-L134) | Enforces RBAC `Level 3 · Admin` for live `tip_live_<16_hex>` key rotation (`AUTH · KeyRot`) and audits RBAC/alert transitions (`AUTH · RBAC`, `WRITE · Alert`) |

---

## 2. Inbound LMS Integration — Canvas LTI 1.3 Webhook & ETL Pipeline

### 2.1 How the Webhook Connects Canvas LMS to OAS
When an instructor evaluates a student's work in **Canvas LMS** using an LTI 1.3 outcomes rubric, Canvas dispatches an HTTP `POST` request to our middleware webhook endpoint (`/api/v2/hooks/canvas-sync/`).

In [`analytics/views.py`](analytics/views.py#L318-L393), `CanvasSyncWebhookAPIView` executes a 5-stage **Extract-Transform-Load (ETL)** pipeline:
1. **Bearer / API Key Extraction & Constant-Time Verification**:
   - `_extract_bearer_token(request)` accepts credentials from either `Authorization: Bearer <token>` or `X-API-Key: <token>` headers to remain compatible with both standard OAuth 2.0 webhook dispatchers and legacy API gateways.
   - The token is verified against `MiddlewareConfig.load().api_secret_key` using `secrets.compare_digest(provided_token, config.api_secret_key)`. Invalid tokens are immediately rejected with `401 Unauthorized`.
2. **Schema Validation via DRF Serializer**:
   - [`CanvasWebhookIngestSerializer`](analytics/serializers.py#L40-L53) validates `course_code`, `canvas_rubric_id`, `student_number`, and the 5-domain `scores` dictionary (`knowledge`, `skills`, `values`, `capstone`, `internship`), clamping values to `0.00–100.00`.
3. **RA 10173 SHA-256 Student Anonymization (Transform Stage)**:
   - Before any database write occurs, the raw student number (e.g., `"2023-10492"`) is irreversibly tokenized:
     ```python
     anon_token = hashlib.sha256(payload['student_number'].encode('utf-8')).hexdigest()
     ```
   - This ensures zero personally identifiable student numbers are ever persisted in the analytics database, satisfying **Republic Act No. 10173 (Data Privacy Act of 2012)**.
4. **Atomic SIS Database Persistence (Load Stage)**:
   - Inside `with transaction.atomic():`, the middleware resolves or auto-provisions the target `Course` (`Course.objects.get_or_create(course_code=payload['course_code'])`) and inserts the anonymized `StudentCompetencyRecord`.
5. **Real-Time Telemetry & Cryptographic Audit Sealing**:
   - Execution latency is measured via `time.perf_counter()` (`elapsed_ms`) and packet throughput (`throughput_pkts`) is recorded in `SyncTelemetryLog`.
   - The canonical JSON payload is hashed via `DPAAuditLog.generate_hash(raw_json)` and persisted as a `SYNC · Canvas` audit row.

### 2.2 Verified Webhook Request & Response Contract

```http
POST /api/v2/hooks/canvas-sync/ HTTP/1.1
Host: localhost:8000
Authorization: Bearer tip_live_98a7bc65d4e3f210
Content-Type: application/json

{
  "course_code": "CPE 515",
  "canvas_rubric_id": "RUB-2026-991",
  "student_number": "2023-10492",
  "scores": {
    "knowledge": 95,
    "skills": 88,
    "values": 92,
    "capstone": 85,
    "internship": 98
  }
}
```

```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "status": "LIVE - SYNCED",
  "latency_ms": 18,
  "throughput_pkts": 1.84,
  "timestamp": "09:45:12",
  "sha256_payload": "6b81f0…3312d4"
}
```

---

## 3. Identity & Access Management (IAM / SSO) Integration

### 3.1 Connecting Institutional Directory Accounts & OAuth 2.0 Sessions
To integrate seamlessly with institutional accounts (`@tip.edu.ph`), the codebase provides two coordinated authentication endpoints in [`analytics/views.py`](analytics/views.py#L437-L558):
1. **`POST /api/v2/auth/session-login/` (`EmpowerEdSessionLoginAPIView`)**:
   - Performs case-insensitive institutional email lookup (`InstitutionalUser.objects.filter(email__iexact=email, is_active=True).first()`) and verifies the password hash via `user.check_password(password)`.
   - On success, issues a fresh per-session OAuth 2.0 bearer token (`_issue_oauth_token()` → `tip_oauth_<24_hex>`), hashes the token via SHA-256 (`token_digest`), and logs an `AUTH · OAuth` entry in `DPAAuditLog` containing only the digest (never the raw token).
   - Sets the `empowered_sessionid` cookie with a **15-minute (`900` seconds) sliding expiration window** (`request.session.set_expiry(900)` and `empowered_last_activity`).
2. **`POST /api/v2/auth/sso/` (`InstitutionalSSOAPIView`)**:
   - Implements the simulated T.I.P. Microsoft OAuth 2.0 + 2FA institutional handshake, synchronizing the user's `role` (`DEAN`) and active RBAC `clearance_level` (`1`–`3`) with `MiddlewareConfig`.
3. **Global Session & Idle Auto-Logout Guard**:
   - Server-side decorator `_empowered_login_required` and client-side watcher `initSessionAutoLogout()` in [`base.js`](analytics/static/javascript/base.js#L36-L65) automatically flush expired sessions and redirect to `/login/?next=<requested-path>`.

---

## 4. Legacy SIS Database & Curriculum ERP Synchronization

### 4.1 Dual-Engine Database Adapter (`SQLite 3` ↔ `PostgreSQL 17`)
Higher education institutions frequently need to bridge local/legacy SQLite stores with enterprise PostgreSQL database clusters. In [`empowered_project/settings.py`](empowered_project/settings.py#L67-L78), our middleware implements a **12-Factor Dual-Engine Database Adapter**:
- When `DATABASE_URL` is omitted, the system connects to the local **SQLite 3** database (`db.sqlite3`) and runs idempotent post-migrate auto-seeding ([`ensure_seed_data()`](analytics/services.py#L80-L180)).
- When `DATABASE_URL` is provided (e.g., `postgres://postgres:pass@db.institution.edu.ph:5432/empowered_v2`), `dj_database_url.config(conn_max_age=600)` and `psycopg[binary]` 3.3 automatically connect to **PostgreSQL 17** with 600-second persistent connection pooling.

### 4.2 Real-Time State Aggregation & Bi-Directional Curriculum Sync
- **Unified State Endpoint (`GET /api/v2/dashboard/state/`)**:
  - `DashboardStateAPIView` aggregates live KPIs (`abet_accreditation`, `ched_obe_status`, `matrix_coverage`, `deficit`), 5-domain competency averages, 6-axis radar coordinates, 10-point latency/throughput telemetry series, ABET Criteria 1–7 lock states, the full `Course × SO1..SO4` matrix, the latest 8 `DPAAuditLog` rows, and the masked OAuth token in a single JSON payload consumed by all frontend panels and external monitoring tools.
- **Curriculum Matrix & ABET Checklist Synchronization (`PATCH /api/v2/matrix/mapping/` & `PATCH /api/v2/abet/criteria/`)**:
  - Allows authorized curriculum planners (`RBAC Level >= 2`) to update `I` / `E` / `R` Student Outcome mappings and lock/unlock ABET Criteria 1–7, immediately recalculating institutional KPIs and recording `WRITE · SO Map` or `WRITE · ABET SSR` audit seals.

---

## 5. Outbound Accreditation & ERP Reporting Integration

To connect internal OBE analytics with external **CHED Regional Quality Assessment Teams (RQAT)** and **ABET Self-Study Report (SSR)** submission workflows, the middleware provides two cryptographically sealed export interfaces:
1. **Automated Binary PDF Export API (`POST /api/v2/reports/abet-ssr/`)**:
   - `ABETReportExportAPIView` validates the requested criteria via `ABETReportExportSerializer`, generates a tamper-evident `EXPORT · PDF` SHA-256 hash in `DPAAuditLog`, compiles a binary A4 PDF (`TIP_EmpowerED_ABET_SSR_v2.pdf`) via `build_abet_ssr_pdf()` using `fpdf2`, and streams it with custom HTTP verification headers:
     - `Content-Type: application/pdf`
     - `Content-Disposition: attachment; filename="TIP_EmpowerED_ABET_SSR_v2.pdf"`
     - `X-Audit-Timestamp: <HH:MM:SS>`
     - `X-Audit-Hash: <first6…last6>`
2. **Two-Phase Sealed Print Portal (`POST /api/v2/reports/abet-print-seal/` → `GET /abet-report/print/?seal=<hash>`)**:
   - `ABETPrintSealAPIView` writes an official `EXPORT · Print` row to `DPAAuditLog` and returns its `sha256_payload`.
   - `abet_report_print_view` performs a pure-read verification query (`DPAAuditLog.objects.filter(sha256_payload=seal, action__startswith='EXPORT').exists()`) before rendering the official RA 10173 DPA Audit Seal on the printable report, preventing unlogged or forged accreditation printouts.

---

*Prepared and verified for **CHED Status 4 — Integration Strategy (OAS)** submission to **Prof. Jose Leo G. Redoblo**.*
