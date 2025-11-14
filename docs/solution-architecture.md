# Churchill Application Portal — Solution Blueprint
**Version:** 1.0  
**Last Updated:** November 14, 2025

## 1. Vision & Guiding Principles
- **Human-centered**: empathize with agents, staff, and students through contextual workflows, smart defaults, and proactive nudges.
- **Single source of truth**: every artifact (forms, documents, chat, statuses) lives in one ecosystem backed by auditable data.
- **Automation first**: leverage OCR, rules engines, and notifications so staff spend time on decisions—not data entry.
- **Composable architecture**: independent services for intake, review, GS workflow, and communications to scale each area separately.

## 2. Recommended Stack
| Layer | Technology | Hosting | Notes |
| --- | --- | --- | --- |
| Frontend | [Next.js 14](https://nextjs.org/) + React + TypeScript, Tailwind UI kit + custom design tokens | Hostinger VPS (Docker) | SSR/ISR for portals, component re-use, strong mobile support |
| State/Data | React Query, Zustand, form libraries (React Hook Form), Recharts for dashboards | Client-side | Keeps UI resilient and optimistic |
| Backend API | FastAPI (Python 3.12) + Pydantic v2 + SQLAlchemy 2 | Hostinger VPS (Docker) | Async-first modular services for Application, Documents, Workflow, Timeline |
| Background Processing | Celery (Redis broker) | Hostinger VPS (Docker) | Handles OCR ingestion, notifications, document rendering pipelines |
| Database | PostgreSQL 16 | Hostinger VPS (Docker) or Railway/Supabase ($10-20/mo) | Primary transactional database for applications, users, timeline |
| Cache/Queue | Redis 7 | Hostinger VPS (Docker) | Celery broker, session cache, rate limiting |
| OCR/AI | Microsoft Azure Form Recognizer (Document Intelligence) | Azure (pay-per-use) | Custom models for apply-at-churchill, GS forms, passports, transcripts (~$5-25/mo for 500 docs) |
| Document Storage | Azure Blob Storage (hot tier) | Azure (pay-per-use) | Versioned documents, OCR output, templates (~$1-2/mo for 50GB) |
| Email | Azure Communication Services | Azure (pay-per-use) | Transactional emails for notifications (~$0.0001/email) |
| E-Signature | DocuSeal (self-hosted) or DocuSign API | Hostinger VPS (Docker) / External API | Hybrid: DocuSeal for low-risk, DocuSign for compliance-heavy |
| Auth | Auth0 Free Tier or custom JWT (FastAPI) | Hostinger VPS / SaaS | Role- and tenant-aware access; MFA for staff/admin |
| Reverse Proxy | Nginx + Let's Encrypt SSL | Hostinger VPS | Handles HTTPS, load balancing, static asset serving |
| Monitoring | Uptime Robot (free) + Sentry (errors) + custom logs | SaaS + VPS | Basic monitoring for MVP; migrate to Azure Monitor at scale |

## 3. Modular Architecture

### 3.0 Deployment Model (MVP: Hostinger VPS + Selective Azure)

**Core Services (Hostinger VPS via Docker)**
```
Hostinger VPS (2 vCPU, 4GB RAM, 100GB SSD ~ $10-17/month)
  ├─ Nginx (reverse proxy, SSL termination)
  ├─ Next.js Frontend (SSR, static assets)
  ├─ FastAPI Backend (API gateway + domain services)
  ├─ Celery Workers (background jobs)
  ├─ PostgreSQL 16 (application database)
  ├─ Redis 7 (cache + Celery broker)
  └─ DocuSeal (self-hosted e-signature for low-risk docs)
```

**Managed Cloud Services (Azure, pay-per-use ~ $7-30/month)**
```
Azure
  ├─ Blob Storage (documents, OCR output, templates)
  ├─ Form Recognizer (OCR pipeline)
  └─ Communication Services (transactional email)
```

**docker-compose.yml structure**:
```yaml
services:
  db:
    image: postgres:16
    volumes: [./data/postgres:/var/lib/postgresql/data]
  
  redis:
    image: redis:7-alpine
  
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - AZURE_BLOB_CONNECTION_STRING=...
      - AZURE_FORM_RECOGNIZER_ENDPOINT=...
    depends_on: [db, redis]
  
  worker:
    build: ./backend
    command: celery -A app.celery worker --loglevel=info
    depends_on: [redis, db]
  
  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
  
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/letsencrypt
    depends_on: [api, frontend]
```

### 3.1 Logical Service Boundaries
```
Frontend Apps (Agent, Staff, Tracker)
        ↓
API Gateway / BFF (GraphQL/REST)
        ↓
Domain Services
 ├─ Application Intake Service
 ├─ Document Service (upload, OCR, preview)
 ├─ Workflow Orchestrator (state machine)
 ├─ Timeline & Notification Service
 ├─ GS Assessment Service
 ├─ Reporting & Analytics Service
 └─ AI Assistant Service
        ↓
Data Stores & Integrations (SQL, Blob, OCR, Email, E-signature)
```

Each domain service is implemented as an independent FastAPI application packaged with shared dependencies (auth, logging, exception handling) and deployed to Azure Container Apps or AKS. Shared Pydantic schemas ensure consistent contracts between the FastAPI BFF, the worker fleet, and any external integrations.

### 3.1 Key Services
1. **Application Intake**
   - Manages digital rendering of `apply-at-churchill.pdf` into wizard-style steps.
   - Autosaves drafts, validates required docs, handles program-specific fields.

2. **Document Service**
   - Orchestrates secure uploads (chunked), virus scanning, storage, and signed URLs.
   - Sends documents to Azure Form Recognizer; merges OCR output into application fields.
   - Maintains preview-ready derivatives (PDF.js-compatible, image thumbnails).

3. **Workflow Orchestrator**
   - Finite-state machine capturing statuses: Draft → Submitted → Staff Review → Offer Decision → Offer Signed → GS Docs → GS Interview → GS Decision → Fee Pending → COE Ready → Complete.
   - Emits events used by notifications, dashboards, and trackers.

4. **GS Assessment Service**
   - Templates for CIHE GS forms, agent checklists, student forms, and staff assessments.
   - Handles digital signature (DocuSign/Azure Sign) and pushes updates to all portals.

5. **Timeline & Notification Service**
   - Asynchronous comment feed (no WebSockets) attached to each application; behaves like a collaborative activity log rather than live chat.
   - Every system/user event is persisted as a timeline entry with actor, timestamp, stage, linked documents, and optional mentions/attachments.
   - Notification engine fans out the same events to channels (in-app inbox/toast, transactional email, optional SMS/push) with user-configurable preferences and SLA-based reminders.

6. **Reporting & Analytics**
   - Materialized views for agent submission metrics, staff productivity, stage durations, GS pass/fail ratios.
   - Exports (CSV/PDF) and embedded charts.

7. **AI Assistant / Chatbot**
   - Contextual Q&A scoped to each application's timeline, documents, and workflow history.
   - Powered by RAG (Retrieval-Augmented Generation) over indexed timeline entries, uploaded documents, and GS notes.
   - Backend uses Azure OpenAI (GPT-4) or open-source LLM with vector embeddings stored in Azure AI Search or Pinecone.
   - Agents can ask "What's blocking application #1234?" or "Summarize student's qualifications" and receive sourced answers with citations to timeline/docs.

### 3.2 FastAPI Implementation Patterns
- **Layered routers**: each bounded context (Application, Documents, Workflow, GS, Chat) exposes its own `APIRouter`, registered under a versioned prefix in the gateway FastAPI app.
- **Dependency injection**: shared dependencies for RBAC, tenant resolution, and database sessions use FastAPI's dependency system, backed by SQLAlchemy 2 async engines and sessionmakers.
- **Validation contracts**: Pydantic v2 models define both request/response DTOs and internal domain aggregates, ensuring schema parity with the frontend TypeScript types via codegen.
- **Background orchestration**: long-running jobs (OCR, offer generation, email fan-out) enqueue Celery tasks published to Azure Service Bus/Redis, with FastAPI endpoints emitting task IDs for UI polling.
- **Timeline logging**: shared dependency emits immutable timeline entries for every API mutation, ensuring the comment feed and audit trail stay in sync across portals.
- **Observability**: middleware captures structured logs, OpenTelemetry traces, and metrics pushed to Azure Monitor for per-request visibility.

### 3.3 Notifications & E-sign Strategy
- **Notification preferences**: user-level settings stored per channel with sane defaults; critical compliance alerts bypass mutes.
- **Delivery pipeline**: timeline events → Service Bus topics → FastAPI notification workers that send email (Azure Communication Services), in-app inbox/toasts, and optional SMS/push adapters.
- **Digest & reminders**: nightly Celery tasks assemble digest emails and escalate overdue actions based on workflow SLA metadata.
- **E-sign provider mix**: primary adapter targeting Azure Sign/DocuSign; secondary adapter for DocuSeal/self-hosted signer to reduce per-envelope cost for high-volume documents.
- **Abstraction layer**: FastAPI e-sign module issues envelopes, tracks status, and exposes a consistent API to the portals regardless of provider.

## 4. UX / UI Guidelines
- **Information architecture**: persistent left nav per portal, contextual right drawer for documents/timeline, central timeline.
- **Agent Dashboard**: KPI tiles, submission funnel, quick actions, outstanding tasks card, AI assistant entry point.
- **Application Detail Page**: hero summary (student, intake, owner), stage tracker, tabbed sections (Form, Documents, Timeline, GS, Offer, Fee, COE) with a dedicated chronological feed showing comments and system events.
- **Document Upload UX**: drag-drop area, file checklist, OCR progress indicator, side preview with field mapping.
- **Staff Workbench**: triage board (Kanban/list), bulk assignment, split-pane review (form vs documents).
- **Track My Application**: simplified timeline, tasks checklist, document downloads, e-sign flow.

## 5. Data Model Snapshot (Lean JSONB-First Architecture)

**Architecture:** Lean 16-table schema with aggressive JSONB usage for MVP. Normalize only when actual usage patterns demand it.

**Core Entities:**
- `RTO_PROFILE` (organization/RTO metadata for multi-tenancy)
- `USER_ACCOUNT`, `AGENT_PROFILE`, `STAFF_PROFILE`, `STUDENT_PROFILE` (identity management)
- `COURSE_OFFERING` (course catalog)
- `APPLICATION` (fat model with 10 JSONB fields: `enrollment_data`, `emergency_contacts`, `health_cover_policy`, `disability_support`, `language_cultural_data`, `survey_responses`, `additional_services`, `gs_assessment`, `signature_data`, `form_metadata`)
- `APPLICATION_STAGE_HISTORY` (workflow transitions for SLA reporting)
- `SCHOOLING_HISTORY`, `QUALIFICATION_HISTORY`, `EMPLOYMENT_HISTORY` (frequently-queried history lists)
- `DOCUMENT_TYPE`, `DOCUMENT` (with `gs_document_requests` JSONB), `DOCUMENT_VERSION`
- `TIMELINE_ENTRY` (with `event_payload` JSONB and `correlation_id`)
- `AUDIT_LOG` (immutable compliance trail)

**Design Rationale:**
- **16 tables total** (down from 34, 53% reduction) for rapid MVP iteration
- **JSONB-first philosophy**: Consolidate 19 tables into JSONB fields to avoid premature optimization
- **Normalized tables** retained only for: 
  - Multi-tenancy (RTO_PROFILE for organization metadata)
  - Core workflow (APPLICATION, APPLICATION_STAGE_HISTORY for SLA queries)
  - Frequently-queried history lists (SCHOOLING, QUALIFICATION, EMPLOYMENT)
  - Core domain objects (DOCUMENT versioning, TIMELINE activity feed)
- **External service delegation**: 
  - ❌ NOTIFICATION table → Use Celery task results + in-app toasts
  - ❌ DOCUMENT_TEMPLATE → Azure Blob filename conventions
  - ❌ WORKFLOW_STAGE_SLA → YAML config or USER_ACCOUNT.admin_config JSONB
  - ❌ WORKFLOW_EVENT → Merged into TIMELINE_ENTRY.event_payload
- **Easy migration path**: PostgreSQL JSONB → table promotion via `CREATE TABLE AS SELECT` when query patterns demand it
- **Scale ceiling**: Handles 5,000-20,000 applications with GIN indexes; normalize when exceeding this threshold

### 5.1 Detailed Relational Schema (Lean 16-Table Architecture)
| Table | Purpose | Key Columns / Relationships |
| --- | --- | --- |
| `rto_profile` | **NEW v3.1** - RTO/organization metadata for multi-tenancy | `id`, `name`, `abn`, `cricos_code`, `contact_email`, `contact_phone`, **`address` (JSONB), `brand_settings` (JSONB), `business_settings` (JSONB)**, `is_active`, `created_at`, `updated_at` |
| `user_account` | Base identity for agents, staff, students, admins | `id`, `email`, `password_hash`, `role`, `rto_profile_id` FK, MFA flags, status, **`notification_preferences` (JSONB), `admin_config` (JSONB)** |
| `agent_profile` / `staff_profile` / `student_profile` | Role-specific metadata | FK `user_account_id`; student profile stores personal details, visa info, contact data |
| `course_offering` | Programs/intakes students can apply for | `id`, `course_code`, `intake`, `campus`, `tuition_fee`, `application_deadline` |
| `application` | **FAT MODEL** - Central record with extensive JSONB fields | `id`, FK `student_profile_id`, optional FK `agent_profile_id`, FK `course_offering_id`, `current_stage`, `assigned_staff_id`, `submitted_at`, `decision_at`, **`enrollment_data` (JSONB), `emergency_contacts` (JSONB array), `health_cover_policy` (JSONB), `disability_support` (JSONB), `language_cultural_data` (JSONB), `survey_responses` (JSONB array), `additional_services` (JSONB array), `gs_assessment` (JSONB), `signature_data` (JSONB), `form_metadata` (JSONB)** |
| `application_stage_history` | Stage transitions with timestamps for SLA reporting | FK `application_id`, `from_stage`, `to_stage`, `changed_by`, `changed_at`, `notes` |
| `schooling_history` | Previous schooling entries (1..n) | FK `application_id`, `institution`, `country`, `start_year`, `end_year`, `qualification_level`, `result` |
| `qualification_history` | Past qualifications achieved | FK `application_id`, `qualification_name`, `institution`, `completion_date`, `certificate_number` |
| `employment_history` | Work experience records | FK `application_id`, `employer`, `role`, `start_date`, `end_date`, `responsibilities`, `is_current` |
| `document_type` | Defines required docs per stage | `id`, `code`, `name`, `stage`, `is_mandatory`, `ocr_model_ref` |
| `document` | Metadata for uploaded docs | `id`, FK `application_id`, FK `document_type_id`, `status`, `uploaded_by`, `uploaded_at`, `ocr_status`, **`gs_document_requests` (JSONB array)** |
| `document_version` | Version history, OCR payloads, virus-scan results | FK `document_id`, `blob_url`, `checksum`, `ocr_json`, `preview_url`, `created_at` |
| `timeline_entry` | Unified activity log/comment feed | FK `application_id`, `entry_type`, `actor_id`, `actor_role`, `message`, `stage`, `linked_document_id`, `created_at`, **`event_payload` (JSONB), `correlation_id` (string)** |
| `audit_log` | Immutable system event log for compliance (superset of timeline) | `id`, `entity_type`, `entity_id`, `action`, `actor_id`, `ip_address`, `payload_json`, `timestamp` |
| ~~`workflow_event`~~ | **DEPRECATED v3.0 - Merged into `timeline_entry.event_payload` + `correlation_id`** | ~~FK `application_id`, `event_type`, `payload_json`, `emitted_at`, `correlation_id`~~ |
| ~~`course_enrollment`~~ | **DEPRECATED v3.0 - Consolidated into `application.enrollment_data` (JSONB)** | ~~FK `application_id`, `enrollment_status`, `offer_signed_at`, `fee_received_at`, `coe_uploaded_at`~~ |
| ~~`emergency_contact`~~ | **DEPRECATED v3.0 - Consolidated into `application.emergency_contacts` (JSONB array)** | ~~FK `application_id`, `name`, `relationship`, `phone`, `email`, `address`~~ |
| ~~`health_cover_policy`~~ | **DEPRECATED v3.0 - Consolidated into `application.health_cover_policy` (JSONB)** | ~~FK `application_id`, `provider`, `policy_number`, `start_date`, `end_date`, `coverage_type`~~ |
| ~~`language_cultural_profile`~~ | **DEPRECATED v2.0 - Consolidated into `application.language_cultural_data` (JSONB)** | ~~FK `application_id`, `first_language`, `other_languages`, `indigenous_status`, `country_of_birth`, `citizenship_status`~~ |
| ~~`disability_support`~~ | **DEPRECATED v3.0 - Consolidated into `application.disability_support` (JSONB)** | ~~FK `application_id`, `has_disability`, `disability_details`, `support_required`, `documentation_status`~~ |
| ~~`usi_record`~~ | **DEPRECATED v2.0 - Removed entirely (use external USI validation API directly)** | ~~FK `application_id`, `usi`, `verification_status`, `consent_flag`~~ |
| ~~`additional_service`~~ | **DEPRECATED v3.0 - Service catalog in `application.additional_services` (JSONB array)** | ~~`id`, `name`, `description`, `fee`~~ |
| ~~`application_additional_service`~~ | **DEPRECATED v3.0 - Consolidated into `application.additional_services` (JSONB array)** | ~~FK `application_id`, FK `additional_service_id`, `selected_at`, `notes`~~ |
| ~~`survey_question` / `survey_response`~~ | **DEPRECATED v2.0 - Consolidated into `application.survey_responses` (JSONB array)** | ~~`survey_question`: definition; `survey_response`: FK `application_id`, `question_id`, `answer`, `submitted_at`~~ |
| ~~`notification`~~ | **DEPRECATED v3.0 - Use Celery task results + in-app toasts** | ~~`id`, FK `timeline_entry_id`, FK `recipient_user_id`, `channel`, `status`, `sent_at`, `read_at`~~ |
| ~~`notification_preference`~~ | **DEPRECATED v3.0 - Consolidated into `user_account.notification_preferences` (JSONB)** | ~~FK `user_account_id`, `channel`, `frequency`, `mute_until`, `created_at`~~ |
| ~~`signature_envelope`~~ | **DEPRECATED v3.0 - Consolidated into `application.signature_data` (JSONB)** | ~~FK `application_id`, `provider`, `envelope_id`, `document_bundle`, `status`, `cost_cents`, `expires_at`, `completed_at`~~ |
| ~~`signature_party`~~ | **DEPRECATED v3.0 - Consolidated into `application.signature_data.parties` (JSONB array)** | ~~FK `signature_envelope_id`, `role` (student/agent/staff), `name`, `email`, `auth_method`, `signed_at`, `ip_address`~~ |
| ~~`gs_assessment`~~ | **DEPRECATED v3.0 - Consolidated into `application.gs_assessment` (JSONB)** | ~~FK `application_id`, `staff_id`, `interview_date`, `scorecard_json`, `decision`, `notes`~~ |
| ~~`gs_document_request`~~ | **DEPRECATED v3.0 - Consolidated into `document.gs_document_requests` (JSONB array)** | ~~FK `application_id`, `document_type_id`, `requested_by`, `requested_at`, `due_at`, `status`~~ |
| ~~`document_template`~~ | **DEPRECATED v3.0 - Use Azure Blob filename conventions (e.g., `templates/offer_letter_v2.docx`)** | ~~`id`, `name`, `template_type`, `blob_url`, `version`, `active`~~ |
| ~~`workflow_stage_sla`~~ | **DEPRECATED v3.0 - Use YAML config file or `user_account.admin_config` (JSONB)** | ~~`id`, `stage`, `target_hours`, `escalation_hours`, `notification_template`~~ |
| ~~`staff_admin_config`~~ | **DEPRECATED v3.0 - Consolidated into `user_account.admin_config` (JSONB)** | ~~FK `user_account_id` (admin role), configuration keys/values~~ |

## 6. Integrations & Automations
1. **OCR Pipeline**
   - Upload → Nginx → FastAPI → Azure Blob Storage → Celery worker triggers Azure Form Recognizer → structured data persisted via FastAPI Application Intake APIs.
   - **Cost optimization**: Cache OCR JSON in `document_version.ocr_json` to avoid re-processing; batch documents when possible.
2. **Offer Generation**
   - Celery task fetches template from Blob Storage, invokes Python-docx/ReportLab, uploads signed PDF, then calls Notification service to alert agent & student.
3. **E-signature**
   - Embedded signing sessions keep students inside the portal; DocuSeal (self-hosted) or DocuSign webhook reconciles status back into FastAPI.
   - Pluggable provider adapter: DocuSeal for acknowledgements/forms, DocuSign API for compliance-heavy offer letters & COE if budget allows.
   - Webhook listener validates signatures (HMAC), stores signed PDFs in Blob Storage, and emits timeline + notification events.
4. **Notifications**
   - Celery workers consume timeline events from Redis queue, call Azure Communication Services (email) and persist in-app notifications to PostgreSQL.

## 7. Security & Compliance
- RBAC covering Agent, Staff, Student, Admin, Auditor roles.
- MFA enforced for staff/admin.
- Field-level encryption for sensitive data (passports, financial docs).
- Immutable audit log with append-only storage for compliance.
- **Multi-tenancy model**: single database with row-level security; each agency/institution assigned a `tenant_id` filtering all queries. Future option to shard by tenant if scale demands.
- **Infrastructure security**: VPS firewall (UFW) limiting ports 80/443/22; SSH key-only auth; automated security updates via unattended-upgrades; Nginx rate limiting; PostgreSQL access restricted to localhost/Docker network.

## 8. Cost Optimization & Scaling Strategy

### 8.1 MVP Budget (~$20-35/month)
| Service | Monthly Cost |
|---|---|
| Hostinger VPS 2 (2 vCPU, 4GB RAM) | $10-17 |
| Azure Blob Storage (50GB hot tier) | $1-2 |
| Azure Form Recognizer (500 docs/month) | $5-10 |
| Azure Communication Services (5k emails) | $0.50 |
| DocuSeal self-hosted e-sign | Free |
| Domain + SSL (Let's Encrypt) | Free |
| **Total** | **$16.50-29.50** |

### 8.2 Optimization Tactics
- **OCR caching**: Store parsed JSON in `document_version.ocr_json`; re-use for edits/re-submissions.
- **Image compression**: Resize/compress uploads before storing in Blob (use Pillow in Celery worker).
- **Database indexing**: Add indexes on `application.current_stage`, `timeline_entry.application_id`, `document.uploaded_at`.
- **Nginx static caching**: Serve Next.js static assets with long cache headers; use Cloudflare free CDN in front of VPS.
- **Celery rate limiting**: Batch OCR jobs (process 10 docs at once) to reduce API call overhead.

### 8.3 Migration Path to Azure (500+ apps/month)
When you hit scale or need enterprise SLAs:
1. **Migrate API → Azure Container Apps** (consumption plan, auto-scale 0-10 replicas) ~ $30-80/month.
2. **Migrate Database → Azure Database for PostgreSQL Flexible** (Burstable B1ms) ~ $12/month or keep Railway/Supabase.
3. **Add Azure Application Insights** for monitoring/tracing ~ $5-15/month.
4. **Enable geo-redundant Blob Storage** if compliance requires ~ +30% cost.
5. **Use Azure Front Door** for global load balancing ~ $35/month base + traffic.

**Estimated scale cost (1,000 apps/month)**: $80-150/month full Azure vs $50-80/month hybrid Hostinger+Azure.

## 9. Delivery Roadmap (High-Level)
1. **Foundation Sprint**: Docker-compose setup on Hostinger VPS, FastAPI + Next.js monorepo scaffolding (auth, design system, shared contracts), Azure Blob/OCR integration, basic navigation.
2. **Agent Intake MVP**: digitized form, document uploads, OCR integration, submission.
3. **Staff Review + Offer**: work queue, decisioning, offer generation, notifications.
4. **Track Portal + E-sign**: student tracker, DocuSeal offer signing, progress timeline.
5. **GS Workflow Phase**: GS docs, forms, interviews, decisions.
6. **Payments + COE**: fee upload, COE generation/download, completion automation.
7. **Analytics + AI Assistant**: dashboards, advanced filters, RAG-based conversational assistant.

## 10. Next Steps
- Validate assumptions with stakeholders (fields, compliance).
- Prioritize features per sprint; define acceptance criteria per stage.
- Start UX wireframes for the three portals and the application detail layout.
- **Provision Hostinger VPS**: VPS 2 plan, install Docker + docker-compose, configure UFW firewall, set up SSH keys.
- **Set up Azure resources**: create Blob Storage container, provision Form Recognizer instance, configure Communication Services email domain.
- Bootstrap the FastAPI codebase (base app, routers, auth dependencies, Celery worker, docker-compose.yml) and connect to Azure resources.
- Configure Nginx reverse proxy with Let's Encrypt SSL for production domain.

---

## Changelog
- **v1.0 (2025-11-14)**: Initial architecture defined; FastAPI stack selected, service decomposition complete, detailed schema added, AI assistant integrated, multi-tenancy & SLA config documented.
- **v1.1 (2025-11-14)**: Updated deployment model to Hostinger VPS + Docker + selective Azure services; added cost optimization strategy, docker-compose structure, and Azure migration path.
- **v2.0 (2025-11-14)**: **BREAKING CHANGE** - Refactored database schema to hybrid architecture (section 5). Consolidated `language_cultural_profile`, `usi_record`, `survey_question`, and `survey_response` tables into JSONB columns within `application` table. Reduced from 34 to 28 tables while maintaining query performance. Updated section 5.1 table reference to mark deprecated tables.
- **v3.0 (2025-11-14)**: **MAJOR BREAKING CHANGE** - Adopted lean JSONB-first MVP architecture (section 5 & 5.1). Reduced schema from 34 to 15 tables (56% reduction). Consolidated 19 additional tables into JSONB fields across `APPLICATION` (enrollment_data, emergency_contacts, health_cover_policy, disability_support, additional_services, gs_assessment, signature_data), `USER_ACCOUNT` (notification_preferences, admin_config), `DOCUMENT` (gs_document_requests), and `TIMELINE_ENTRY` (event_payload + correlation_id). Dropped `NOTIFICATION`, `DOCUMENT_TEMPLATE`, `WORKFLOW_STAGE_SLA`, `WORKFLOW_EVENT` tables (replaced by Celery logs, Azure Blob conventions, config files, timeline consolidation). Updated design rationale to emphasize rapid MVP iteration with clear JSONB→table promotion path when scale demands normalization.
- **v3.1 (2025-11-14)**: Added `RTO_PROFILE` table for organization/multi-tenancy management (15 → 16 tables, 53% reduction from v1.0). Renamed `USER_ACCOUNT.tenant_id` to `rto_profile_id`. RTO_PROFILE stores RTO metadata (name, ABN, CRICOS, contact info) with JSONB fields for branding (logo, colors) and business settings (commission rates, SLA overrides). Enables future multi-RTO SaaS expansion while keeping MVP lean for Churchill Education.
