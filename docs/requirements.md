# Churchill Application Portal — Initial Requirements
**Version:** 1.0  
**Last Updated:** November 14, 2025

## 1. Experience & UX
- Responsive web app optimized for desktop and mobile.
- Visually rich, trustworthy design system with clear hierarchy and friendly micro-interactions.
- Clear, sectioned layout when viewing an application, with contextual actions and status timeline.

## 2. Multi-Portal Structure
1. **Agent Portal**
   - Digitized version of `apply-at-churchill.pdf` with progressive sections, autosave, validation, and contextual help.
   - Microsoft OCR-assisted intake: document upload triggers OCR extraction to pre-fill form fields, with editable confirmation and side-by-side preview.
   - Document requirements: Passport, SLC Transcript, HSC Transcript, English Test, plus "Other" document slots with custom labels.
   - Application assignment metadata so each submission can be routed to specific Churchill staff members.
   - Dashboard showing submission counts, status breakdown, overdue tasks, and smart insights.
   - Real-time progress tracker per application.
   - AI-powered assistant scoped to the selected application and its history, answering questions about status, blockers, and requirements.
   - Advanced filtering, saved views, and exportable reports.
   - Ability to upload additional/requested documents post-submission.
   - Notifications (in-app + email) when staff request info or status changes.

2. **University Staff Portal**
   - Work queue of assigned applications with stage filters.
   - Review tools to approve or reject applications; approvals trigger automated offer-letter generation and delivery.
   - Offer letters available for agent download; system emails agents when action is required.
   - Student e-signature capture for offers, with status tracking.
   - GS (Genuine Student) workflow management: track uploads for Financial, Relation Proof, Tax Income, Business Income, Other documents.
   - Digital completion of `CIHE GS Form Agent GS Checklist- Agent.docx`, `GS Form Student To Complete.docx`, and `GS Assessment Form Staff.docx` with audit trails and attachments.
   - Staff interview scheduling and recording within the system; decisions recorded in portal.
   - Fee payment reminder/receipt upload once GS is approved; staff can upload COE for download.
   - Staff performance and workload tracking, stage-level analytics, and flexible reporting.
   - Timeline view for each application showing all agent/student/staff interactions and system events.
   - **Admin panel** for managing course offerings, intakes, document types, SLA rules, and offer letter templates.

3. **Track My Application (Student/Agent view)**
   - Real-time status timeline with milestone details (Submission, Offer Review, Offer Sent, Offer Signed, GS Review, GS Decision, Fee Payment, COE Issued).
   - Secure document preview/download (offer letters, COE, submitted files).
   - Signature capture and outstanding task checklist (e.g., upload GS docs, sign forms).
   - Timeline/comment feed tied to the application showing all updates and staff messages.

## 3. Automation & Integrations
- Microsoft OCR service for document ingestion and auto-fill.
- Email + in-app notifications for every workflow transition (assignment, info requests, approvals, offers, GS decisions, fee receipt, COE upload) with configurable reminders and digests.
- Webhooks or background jobs to push signed student forms back into all portals and update statuses.

## 4. Notifications & Timeline
- Every action (manual or automated) must create a timeline entry visible to agents, staff, and students with actor, timestamp, stage, linked documents, and next steps.
- Notification center surfaces unread timeline items, pending tasks, and SLA breaches; users can filter by application or event type.
- Multiple channels supported from day one: in-app toasts + inbox, transactional email, and optional SMS/push in later releases.
- Users can configure notification preferences (immediate, batched, mute per application) while critical compliance alerts always send.

## 5. Security & Compliance
- Role-based access (Agent, Staff, Student/Viewer) with least privilege.
- Document storage with audit trails, versioning, and preview safeguards.
- E-signature compliant with relevant regulations (capture IP, timestamp, intent).
- Logging of all actions for traceability.

## 6. Reporting & Analytics
- Agent-side reports for submissions, approval rates, pending actions.
- Staff-side reports for workload distribution, turnaround time, stage throughput, and GS pass/fail metrics.
- University-wide dashboards with filters by region, agent, program, intake, and staff member.

## 7. Future Considerations / Nice-to-haves
- Configurable workflow builder for new document types or stages.
- Template-driven messaging center for consistent communications.
- Mobile push notifications if a companion app is introduced.
- Localization support for international agents/students.

## 8. Technical Constraints
- Backend services must be implemented with FastAPI (Python 3.12+) to ensure high-performance async APIs and alignment with the engineering stack.
- Shared Pydantic schemas should define the contract between portals, background workers, and integrations.
- Celery (or Azure Functions bindings) will power background pipelines such as OCR processing, notifications, and document generation.

---

## Changelog
- **v1.0 (2025-11-14)**: Initial requirements captured; added notifications/timeline section, AI assistant, admin panel, technical constraints.
