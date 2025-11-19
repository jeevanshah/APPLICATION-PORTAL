"""
Application service.
Handles application business logic, progress tracking, and workflow.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Application, ApplicationStage, UserRole
from app.repositories.agent import AgentRepository
from app.repositories.application import ApplicationRepository
from app.repositories.student import StudentRepository
from app.repositories.user import UserRepository


class ApplicationError(Exception):
    """Base exception for application-related errors."""
    pass


class ApplicationNotFoundError(ApplicationError):
    """Raised when application is not found."""
    pass


class ApplicationPermissionError(ApplicationError):
    """Raised when user lacks permission for application operation."""
    pass


class ApplicationValidationError(ApplicationError):
    """Raised when application data validation fails."""
    pass


class ApplicationService:
    """Service for application business logic."""

    def __init__(self, db: Session):
        """
        Initialize application service.

        Args:
            db: Database session
        """
        self.db = db
        self.app_repo = ApplicationRepository(db)
        self.student_repo = StudentRepository(db)
        self.agent_repo = AgentRepository(db)
        self.user_repo = UserRepository(db)

    def create_draft(
        self,
        course_offering_id: UUID,
        student_profile_id: Optional[UUID] = None,
        agent_profile_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        user_role: Optional[UserRole] = None
    ) -> Application:
        """
        Create new application draft.

        Args:
            course_offering_id: Course offering UUID
            student_profile_id: Optional student profile UUID (will be created at enrollment if not provided)
            agent_profile_id: Optional agent profile UUID
            user_id: User creating the application
            user_role: Role of creating user

        Returns:
            Created application

        Raises:
            ApplicationPermissionError: If non-agent user tries to create
            ApplicationValidationError: If validation fails
        """
        # Only agents can create applications
        if user_role != UserRole.AGENT:
            raise ApplicationPermissionError(
                "Only agents can create applications on behalf of students")

        # If student_profile_id provided, validate it exists
        if student_profile_id:
            student = self.student_repo.get_by_id(student_profile_id)
            if not student:
                raise ApplicationValidationError("Student profile not found")

        # If agent is creating, automatically use their agent_profile_id
        final_agent_profile_id = agent_profile_id
        if user_role == UserRole.AGENT:
            agent = self.agent_repo.get_by_user_id(user_id)
            if not agent:
                raise ApplicationValidationError(
                    "Agent profile not found for user")

            # If agent_profile_id was provided, verify it matches the user's
            # agent profile
            if agent_profile_id and agent_profile_id != agent.id:
                raise ApplicationPermissionError(
                    "Cannot create application for another agent")

            # Use the agent's profile ID
            final_agent_profile_id = agent.id

        # Create draft application
        app = self.app_repo.create(
            student_profile_id=student_profile_id,
            agent_profile_id=final_agent_profile_id,
            course_offering_id=course_offering_id,
            current_stage=ApplicationStage.DRAFT
        )

        self.db.commit()
        return app

    def get_application(
        self,
        application_id: UUID,
        user_id: Optional[UUID] = None,
        user_role: Optional[UserRole] = None
    ) -> Application:
        """
        Get application by ID with permission check.

        Args:
            application_id: Application UUID
            user_id: Requesting user UUID
            user_role: Requesting user role

        Returns:
            Application with relations

        Raises:
            ApplicationNotFoundError: If not found
            ApplicationPermissionError: If no access
        """
        app = self.app_repo.get_with_relations(application_id)

        if not app:
            raise ApplicationNotFoundError("Application not found")

        # Check read permission
        if user_role == UserRole.STUDENT:
            # Students can only view their own applications
            student = self.student_repo.get_by_user_id(user_id)
            if not student or app.student_profile_id != student.id:
                raise ApplicationPermissionError(
                    "Cannot view this application")

        elif user_role == UserRole.AGENT:
            # Agents can only view applications they created
            agent = self.agent_repo.get_by_user_id(user_id)
            if not agent or app.agent_profile_id != agent.id:
                raise ApplicationPermissionError(
                    "Cannot view this application")

        # Staff and admin can view all applications

        return app

    def list_applications(
        self,
        user_id: UUID,
        user_role: UserRole,
        skip: int = 0,
        limit: int = 100,
        stage: Optional[ApplicationStage] = None
    ) -> List[Application]:
        """
        List applications based on user role.

        Args:
            user_id: Requesting user UUID
            user_role: Requesting user role
            skip: Pagination offset
            limit: Max results
            stage: Optional stage filter

        Returns:
            List of applications user can access
        """
        if user_role == UserRole.STUDENT:
            # Get student's applications
            student = self.student_repo.get_by_user_id(user_id)
            if not student:
                return []

            apps = self.app_repo.get_by_student(
                student_id=student.id,
                skip=skip,
                limit=limit
            )

            # Filter by stage if specified
            if stage:
                apps = [a for a in apps if a.current_stage == stage]

            return apps

        elif user_role == UserRole.AGENT:
            # Get agent's applications
            agent = self.agent_repo.get_by_user_id(user_id)
            if not agent:
                return []

            apps = self.app_repo.get_by_agent(
                agent_id=agent.id,
                skip=skip,
                limit=limit
            )

            if stage:
                apps = [a for a in apps if a.current_stage == stage]

            return apps

        elif user_role in [UserRole.STAFF, UserRole.ADMIN]:
            # Staff/admin can see all or assigned applications
            if stage:
                return self.app_repo.get_by_stage(
                    stage=stage,
                    skip=skip,
                    limit=limit
                )
            else:
                return self.app_repo.get_all(skip=skip, limit=limit)

        return []

    def update_application(
        self,
        application_id: UUID,
        update_data: Dict[str, Any],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """
        Update application fields.

        Args:
            application_id: Application UUID
            update_data: Fields to update
            user_id: Updating user UUID
            user_role: Updating user role

        Returns:
            Updated application

        Raises:
            ApplicationNotFoundError: If not found
            ApplicationPermissionError: If no edit permission
            ApplicationValidationError: If validation fails
        """
        # Get application
        app = self.app_repo.get_by_id(application_id)
        if not app:
            raise ApplicationNotFoundError("Application not found")

        # Only allow updates on DRAFT applications
        if app.current_stage != ApplicationStage.DRAFT:
            raise ApplicationValidationError(
                f"Cannot update application in {
                    app.current_stage.value} stage. Only DRAFT applications can be edited.")

        # Students cannot edit
        if user_role == UserRole.STUDENT:
            raise ApplicationPermissionError(
                "Students cannot edit applications. Please contact your agent.")

        # Agents can only edit their own applications
        if user_role == UserRole.AGENT:
            agent = self.agent_repo.get_by_user_id(user_id)
            if not agent or app.agent_profile_id != agent.id:
                raise ApplicationPermissionError(
                    "Agents can only edit their own applications")

        # Update fields
        for key, value in update_data.items():
            if hasattr(
                    app, key) and key != 'form_metadata':  # Handle form_metadata separately
                setattr(app, key, value)

        # Update form_metadata with deep merge to preserve existing data
        if app.form_metadata:
            metadata = app.form_metadata.copy() if isinstance(app.form_metadata, dict) else {}
        else:
            metadata = {}

        # Initialize metadata structure if needed
        if 'version' not in metadata:
            metadata['version'] = '1.0'
        if 'completed_sections' not in metadata:
            metadata['completed_sections'] = []

        metadata['last_saved_at'] = datetime.utcnow().isoformat()
        metadata['auto_save_count'] = metadata.get('auto_save_count', 0) + 1

        if 'form_metadata' in update_data:
            # Deep merge incoming metadata to preserve existing step data
            incoming = update_data['form_metadata']
            if isinstance(incoming, dict):
                for key, value in incoming.items():
                    # Don't overwrite metadata tracking fields
                    if key not in ['version', 'completed_sections', 'last_saved_at', 'auto_save_count', 
                                   'ip_address', 'user_agent', 'submission_duration_seconds', 'last_edited_section']:
                        metadata[key] = value

        app.form_metadata = metadata
        app.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(app)
        return app

    def submit_application(
        self,
        application_id: UUID,
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """
        Submit application for review.

        Args:
            application_id: Application UUID
            user_id: Submitting user UUID
            user_role: Submitting user role

        Returns:
            Submitted application

        Raises:
            ApplicationNotFoundError: If not found
            ApplicationPermissionError: If no permission
            ApplicationValidationError: If validation fails
        """
        # Get application
        app = self.app_repo.get_by_id(application_id)
        if not app:
            raise ApplicationNotFoundError("Application not found")

        # Validate application is in draft stage
        if app.current_stage != ApplicationStage.DRAFT:
            raise ApplicationValidationError(
                f"Application already submitted (current stage: {
                    app.current_stage.value})")

        # Students cannot submit
        if user_role == UserRole.STUDENT:
            raise ApplicationPermissionError(
                "Students cannot submit applications. Please contact your agent.")

        # Agents can only submit their own applications
        if user_role == UserRole.AGENT:
            agent = self.agent_repo.get_by_user_id(user_id)
            if not agent or app.agent_profile_id != agent.id:
                raise ApplicationPermissionError(
                    "Agents can only submit their own applications")

        # TODO: Add validation for required fields
        # For now, just transition to SUBMITTED

        app = self.app_repo.update_stage(
            application_id=application_id,
            new_stage=ApplicationStage.SUBMITTED,
            notes="Application submitted for review"
        )

        self.db.commit()
        return app

    def calculate_progress(self, application_id: UUID) -> int:
        """
        Calculate application completion percentage.

        Args:
            application_id: Application UUID

        Returns:
            Completion percentage (0-100)
        """
        app = self.app_repo.get_by_id(application_id)
        if not app:
            return 0

        # Count completed steps from form_metadata
        if app.form_metadata and "completed_sections" in app.form_metadata:
            completed = len(app.form_metadata.get("completed_sections", []))
            total_steps = 12  # As per API spec
            return int((completed / total_steps) * 100)

        return 0

    def assign_to_staff(
        self,
        application_id: UUID,
        staff_id: UUID,
        assigning_user_role: UserRole
    ) -> Application:
        """
        Assign application to staff member.

        Args:
            application_id: Application UUID
            staff_id: Staff profile UUID
            assigning_user_role: Role of user making assignment

        Returns:
            Updated application

        Raises:
            ApplicationNotFoundError: If not found
            ApplicationPermissionError: If no permission
        """
        # Only staff/admin can assign
        if assigning_user_role not in [UserRole.STAFF, UserRole.ADMIN]:
            raise ApplicationPermissionError(
                "Only staff can assign applications")

        app = self.app_repo.assign_to_staff(application_id, staff_id)
        if not app:
            raise ApplicationNotFoundError("Application not found")

        self.db.commit()
        return app

    def change_stage(
        self,
        application_id: UUID,
        new_stage: ApplicationStage,
        notes: Optional[str] = None,
        user_role: UserRole = None
    ) -> Application:
        """
        Change application stage.

        Args:
            application_id: Application UUID
            new_stage: New stage
            notes: Transition notes
            user_role: Role of user making change

        Returns:
            Updated application

        Raises:
            ApplicationNotFoundError: If not found
            ApplicationPermissionError: If no permission
        """
        # Only staff/admin can change stages
        if user_role not in [UserRole.STAFF, UserRole.ADMIN]:
            raise ApplicationPermissionError(
                "Only staff can change application stages")

        app = self.app_repo.update_stage(
            application_id=application_id,
            new_stage=new_stage,
            notes=notes
        )

        if not app:
            raise ApplicationNotFoundError("Application not found")

        self.db.commit()
        return app

    def get_dashboard_stats(
        self,
        user_id: UUID,
        user_role: UserRole
    ) -> Dict[str, int]:
        """
        Get dashboard statistics for user.

        Args:
            user_id: User UUID
            user_role: User role

        Returns:
            Dictionary of statistics
        """
        stats = {
            "total_applications": 0,
            "draft_count": 0,
            "submitted_count": 0,
            "in_review_count": 0,
            "offers_count": 0,
            "enrolled_count": 0,
        }

        # Get applications based on role
        apps = self.list_applications(
            user_id=user_id,
            user_role=user_role,
            skip=0,
            limit=1000  # Get all for stats
        )

        stats["total_applications"] = len(apps)

        for app in apps:
            if app.current_stage == ApplicationStage.DRAFT:
                stats["draft_count"] += 1
            elif app.current_stage in [ApplicationStage.SUBMITTED, ApplicationStage.STAFF_REVIEW]:
                stats["in_review_count"] += 1
            elif app.current_stage == ApplicationStage.OFFER_GENERATED:
                stats["offers_count"] += 1
            elif app.current_stage == ApplicationStage.ENROLLED:
                stats["enrolled_count"] += 1

        stats["submitted_count"] = stats["total_applications"] - \
            stats["draft_count"]

        return stats

    # ========================================================================
    # 12-STEP APPLICATION FORM METHODS
    # ========================================================================

    def _update_step_metadata(self, app: Application, step_name: str) -> None:
        """Update form metadata when a step is completed."""
        if not app.form_metadata:
            app.form_metadata = {}

        metadata = app.form_metadata.copy() if isinstance(app.form_metadata, dict) else {}

        # Add step to completed sections if not already there
        completed_sections = metadata.get("completed_sections", [])
        if step_name not in completed_sections:
            completed_sections.append(step_name)
            metadata["completed_sections"] = completed_sections

        metadata["last_edited_section"] = step_name
        metadata["last_saved_at"] = datetime.utcnow().isoformat()

        app.form_metadata = metadata

    def update_personal_details(
        self,
        application_id: UUID,
        data: Dict[str, Any],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 1: Personal Details."""
        # Store in dedicated personal_details JSONB column
        update_data = {
            "personal_details": data
        }

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "personal_details")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_emergency_contact(
        self,
        application_id: UUID,
        contacts: List[Dict[str, Any]],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 2: Emergency Contacts."""
        # Validate at least one primary contact
        has_primary = any(contact.get('is_primary', False)
                          for contact in contacts)
        if not has_primary:
            raise ApplicationValidationError(
                "At least one emergency contact must be marked as primary")

        update_data = {"emergency_contacts": contacts}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "emergency_contact")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_health_cover(
        self,
        application_id: UUID,
        health_data: Dict[str, Any],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 3: Health Cover (OSHC)."""
        update_data = {"health_cover_policy": health_data}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "health_cover")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_language_cultural(
        self,
        application_id: UUID,
        language_data: Dict[str, Any],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 4: Language & Cultural Background."""
        update_data = {"language_cultural_data": language_data}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "language_cultural")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_disability_support(
        self,
        application_id: UUID,
        disability_data: Dict[str, Any],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 5: Disability Support."""
        update_data = {"disability_support": disability_data}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "disability")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_schooling_history(
        self,
        application_id: UUID,
        schooling_entries: List[Dict[str, Any]],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 6: Schooling History."""
        # Store in dedicated schooling_history JSONB column
        update_data = {
            "schooling_history": schooling_entries
        }

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "schooling")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_qualifications(
        self,
        application_id: UUID,
        qualification_entries: List[Dict[str, Any]],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 7: Previous Qualifications."""
        # Store in dedicated qualifications JSONB column
        update_data = {
            "qualifications": qualification_entries
        }

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "previous_qualifications")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_employment_history(
        self,
        application_id: UUID,
        employment_entries: List[Dict[str, Any]],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 8: Employment History."""
        # Store in dedicated employment_history JSONB column
        update_data = {
            "employment_history": employment_entries
        }

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "employment")
        self.db.commit()
        self.db.refresh(app)

        return app
        self.db.refresh(app)

        return app

    def update_usi(
        self,
        application_id: UUID,
        usi: str,
        consent: bool,
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 9: USI."""
        update_data = {"usi": usi}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "usi")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_additional_services(
        self,
        application_id: UUID,
        services: List[Dict[str, Any]],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 10: Additional Services."""
        update_data = {"additional_services": services}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "additional_services")
        self.db.commit()
        self.db.refresh(app)

        return app

    def update_survey(
        self,
        application_id: UUID,
        survey_data: Dict[str, Any],
        user_id: UUID,
        user_role: UserRole
    ) -> Application:
        """Update Step 11: Survey."""
        update_data = {"survey_responses": survey_data.get("responses", [])}

        app = self.update_application(
            application_id, update_data, user_id, user_role)
        self._update_step_metadata(app, "survey")
        self.db.commit()
        self.db.refresh(app)

        return app

    def _can_edit(
            self,
            app: Application,
            user_id: UUID,
            user_role: UserRole) -> bool:
        """Check if user can edit application."""
        if user_role == UserRole.STUDENT:
            return False

        if user_role in [UserRole.STAFF, UserRole.ADMIN]:
            return True

        if user_role == UserRole.AGENT:
            agent = self.agent_repo.get_by_user_id(user_id)
            if agent and app.agent_profile_id == agent.id and app.current_stage == ApplicationStage.DRAFT:
                return True

        return False
