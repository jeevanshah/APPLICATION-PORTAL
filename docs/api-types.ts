/**
 * TypeScript Type Definitions for Application Portal API
 * 
 * Generated from backend schemas - use these types in your frontend application
 * to ensure type safety when working with the API.
 */

// ============================================================================
// Authentication Types
// ============================================================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: UserInfo;
}

export interface UserInfo {
  id: string;
  email: string;
  role: UserRole;
  status: UserStatus;
}

export type UserRole = "STUDENT" | "AGENT" | "STAFF" | "ADMIN";
export type UserStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";

// ============================================================================
// Application Types
// ============================================================================

export interface Application {
  id: string;
  student_profile_id: string;
  course_offering_id: string;
  agent_profile_id: string | null;
  assigned_staff_id: string | null;
  current_stage: ApplicationStage;
  form_metadata?: FormMetadata;
  created_at: string;
  updated_at: string;
}

export type ApplicationStage = 
  | "DRAFT" 
  | "SUBMITTED" 
  | "UNDER_REVIEW" 
  | "APPROVED" 
  | "REJECTED" 
  | "ENROLLED";

export interface FormMetadata {
  completed_sections?: string[];
  last_saved_at?: string;
  auto_save_count?: number;
}

export interface CreateApplicationRequest {
  student_profile_id: string;
  course_offering_id: string;
  agent_profile_id?: string; // Optional - auto-assigned for agents
}

export interface CreateApplicationResponse {
  application: Application;
  message: string;
}

// ============================================================================
// Step Update Response (Common for all steps)
// ============================================================================

export interface StepUpdateResponse {
  success: boolean;
  message: string;
  step_number: number;
  step_name: string;
  completion_percentage: number; // 0-100
  next_step: string | null;
  can_submit: boolean;
}

// ============================================================================
// Step 1: Personal Details
// ============================================================================

export interface PersonalDetailsRequest {
  given_name: string;
  middle_name?: string;
  family_name: string;
  date_of_birth: string; // YYYY-MM-DD
  gender: Gender;
  email: string;
  phone: string;
  street_address: string;
  suburb: string;
  state: string;
  postcode: string;
  country: string;
  passport_number: string;
  passport_expiry?: string; // YYYY-MM-DD
  nationality: string;
  country_of_birth: string;
}

export type Gender = "Male" | "Female" | "Other" | "Prefer not to say";

// ============================================================================
// Step 2: Emergency Contact
// ============================================================================

export interface EmergencyContactRequest {
  contacts: EmergencyContact[];
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
  email?: string;
  is_primary: boolean;
}

// ============================================================================
// Step 3: Health Cover
// ============================================================================

export interface HealthCoverRequest {
  provider: string;
  policy_number: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  coverage_type: string;
}

// ============================================================================
// Step 4: Language & Cultural Background
// ============================================================================

export interface LanguageCulturalRequest {
  first_language: string;
  other_languages: string[];
  english_proficiency: EnglishProficiency;
  requires_language_support: boolean;
  cultural_background: string;
  indigenous_status: IndigenousStatus;
}

export type EnglishProficiency = "Native" | "Fluent" | "Intermediate" | "Basic" | "Minimal";

export type IndigenousStatus = 
  | "Aboriginal"
  | "Torres Strait Islander"
  | "Both Aboriginal and Torres Strait Islander"
  | "Neither Aboriginal nor Torres Strait Islander";

// ============================================================================
// Step 5: Disability Support
// ============================================================================

export interface DisabilitySupportRequest {
  has_disability: boolean;
  disability_type?: string;
  support_required?: string;
  previous_support?: string;
  consent_to_share: boolean;
}

// ============================================================================
// Step 6: Schooling History
// ============================================================================

export interface SchoolingHistoryRequest {
  schools: SchoolRecord[];
}

export interface SchoolRecord {
  school_name: string;
  country: string;
  years_attended: string;
  qualification: string;
  year_completed: number;
}

// ============================================================================
// Step 7: Previous Qualifications
// ============================================================================

export interface PreviousQualificationsRequest {
  qualifications: QualificationRecord[];
}

export interface QualificationRecord {
  institution: string;
  qualification_name: string;
  field_of_study: string;
  country: string;
  year_completed: number;
  grade_average: string;
}

// ============================================================================
// Step 8: Employment History
// ============================================================================

export interface EmploymentHistoryRequest {
  employment_records: EmploymentRecord[];
}

export interface EmploymentRecord {
  employer: string;
  position: string;
  start_date: string; // YYYY-MM-DD
  end_date: string | null; // YYYY-MM-DD or null if current
  is_current: boolean;
  responsibilities: string;
}

// ============================================================================
// Step 9: USI
// ============================================================================

export interface USIRequest {
  usi: string; // Exactly 10 characters
  consent_to_verify: boolean;
}

// ============================================================================
// Step 10: Additional Services
// ============================================================================

export interface AdditionalServicesRequest {
  services: ServiceRequest[];
}

export interface ServiceRequest {
  service_type: string;
  is_required: boolean;
  notes?: string;
}

// ============================================================================
// Step 11: Survey
// ============================================================================

export interface SurveyRequest {
  responses: SurveyResponse[];
}

export interface SurveyResponse {
  question: string;
  answer: string;
}

// ============================================================================
// Step 12: Document Status
// ============================================================================

export interface DocumentStatusResponse {
  required_documents: DocumentInfo[];
  all_uploaded: boolean;
  completion_percentage: number;
}

export interface DocumentInfo {
  document_type: string;
  display_name: string;
  is_uploaded: boolean;
  uploaded_at: string | null;
}

// ============================================================================
// Error Types
// ============================================================================

export interface APIError {
  detail: string | ValidationError[];
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// ============================================================================
// Utility Types
// ============================================================================

export type StepName = 
  | "personal_details"
  | "emergency_contact"
  | "health_cover"
  | "language_cultural"
  | "disability"
  | "schooling"
  | "qualifications"
  | "employment"
  | "usi"
  | "additional_services"
  | "survey"
  | "document";

export interface StepInfo {
  number: number;
  name: StepName;
  displayName: string;
  isComplete: boolean;
}

// ============================================================================
// API Client Helper Types
// ============================================================================

export interface APIConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

export interface RequestOptions {
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  headers?: Record<string, string>;
  body?: any;
  params?: Record<string, string | number>;
}

export interface APIResponse<T> {
  data: T;
  status: number;
  statusText: string;
}
