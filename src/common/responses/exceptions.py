import re

# Человекочитаемые пояснения к незаполненным полям заявки / профиля (ключи
# совпадают с `missing` в сводке перед отправкой). Остальные поля — "Required".
REQUIRED_FIELD_MESSAGES: dict[str, str] = {
    "subject_type": "Select the subject type",
    "legal_name": "Legal name is required for this subject type",
    "bank_id": "Select an active bank that works with this subject type",
    "location": "Set the business location: coordinates, region, district and makhalla",
    "location.confirmed": "Confirm that this is the business location",
    "founders": "Add at least one founder (MCHJ)",
    "photos": "Too many photos attached",
    "documents": "Too many documents attached",
    "company.inn": "Company INN (STIR) is required",
    "company.director_full_name": "Director full name is required",
    "company.director_passport": "Director passport is required",
    "company.director_phone": "Director phone is required",
    "company.director_date_of_birth": "Director date of birth is required",
    "project.requested_amount": "Requested amount is required",
    "project.loan_term_months": "Loan term is required",
    "project.total_cost": "Total project cost is required",
    "project.jobs_count": "Number of jobs to be created is required",
    "project.description": "Project description is required",
    "applicant.phone": "Fill in your phone in the profile",
    "applicant.passport_number": "Fill in your passport in the profile",
    "applicant.inn": "Fill in your INN in the profile",
    "applicant.email": "Fill in your email in the profile",
    "applicant.gender": "Fill in your gender in the profile",
    "applicant.date_of_birth": "Fill in your date of birth in the profile",
    "phone": "Phone is required",
    "passport_number": "Passport is required",
    "inn": "INN is required",
    "email": "Email is required",
    "gender": "Gender is required",
    "date_of_birth": "Date of birth is required",
}


def missing_to_errors(missing: list[str]) -> list[dict]:
    return [
        {"field": field, "message": REQUIRED_FIELD_MESSAGES.get(field, "Required")}
        for field in missing
    ]


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


class ApiException(Exception):
    """Базовое исключение API.

    Ответ: ``{"success": false, "message": ..., "code": ..., "errors": [...] | null}``.
    ``code`` — машиночитаемый код (по умолчанию из имени класса:
    ``ApplicationNotEditableException`` → ``application_not_editable``).
    ``field`` — поле запроса, к которому относится ошибка; попадает в ``errors``.
    """

    status_code = 400
    message = "Bad request"
    code = "bad_request"
    field: str | None = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "code" not in cls.__dict__:
            cls.code = _snake(cls.__name__.removesuffix("Exception"))

    def __init__(
        self,
        message: str | None = None,
        *,
        field: str | None = None,
        errors: list[dict] | None = None,
    ):
        self.message = message or self.message
        if field is not None:
            self.field = field
        self.errors = errors
        super().__init__(self.message)

    def to_errors(self) -> list[dict] | None:
        if self.errors:
            return self.errors
        missing = getattr(self, "missing", None)
        if missing:
            return missing_to_errors(missing)
        if self.field:
            return [{"field": self.field, "message": self.message}]
        return None


# ---------- 401 ----------


class UnauthorizedException(ApiException):
    status_code = 401
    message = "Unauthorized"


class InvalidTokenException(UnauthorizedException):
    message = "Invalid token"


class ExpiredTokenException(UnauthorizedException):
    message = "Access token expired"


class InvalidTokenTypeException(UnauthorizedException):
    message = "Invalid token type"


class NotAuthenticatedException(UnauthorizedException):
    message = "Not authenticated"


class InvalidCredentialsException(UnauthorizedException):
    message = "Invalid username or password"


class RefreshTokenNotFoundException(UnauthorizedException):
    message = "Refresh token not found"


class RefreshTokenRevokedException(UnauthorizedException):
    message = "Refresh token revoked"


class ExpiredRefreshTokenException(UnauthorizedException):
    message = "Refresh token expired"


class SSOException(UnauthorizedException):
    message = "YIA Portal authentication failed. Please try again."


# ---------- 403 ----------


class ForbiddenException(ApiException):
    status_code = 403
    message = "Forbidden"


class PermissionDeniedException(ForbiddenException):
    message = "You do not have permission to perform this action"


class UserBlockedException(ForbiddenException):
    message = "User is blocked"


class ApplicationAccessDeniedException(ForbiddenException):
    message = "You do not have access to this application"


# ---------- 404 ----------


class NotFoundException(ApiException):
    status_code = 404
    message = "Not found"


class UserNotFoundException(NotFoundException):
    message = "User not found"


class RoleNotFoundException(NotFoundException):
    message = "Role not found"


class BankNotFoundException(NotFoundException):
    message = "Bank not found or inactive"
    field = "bank_id"


class ApplicationNotFoundException(NotFoundException):
    message = "Application not found"


class PhotoNotFoundException(NotFoundException):
    message = "Photo not found in this application"


class DocumentNotFoundException(NotFoundException):
    message = "Document not found in this application"


class DemandDocumentNotFoundException(NotFoundException):
    message = "Demand document not found"


class CouncilAssignmentNotFoundException(NotFoundException):
    message = "Application is not assigned to you"


# ---------- 400 / 409 ----------


class BadRequestException(ApiException):
    status_code = 400
    message = "Bad request"


class ConflictException(ApiException):
    status_code = 409
    message = "Conflict"


class InvalidCurrentPasswordException(BadRequestException):
    message = "Current password is incorrect"


class SamePasswordException(BadRequestException):
    message = "New password must differ from the current one"


class PasswordLoginNotAllowedException(BadRequestException):
    message = "Password login is not set up for this user"


class UsernameAlreadyExistsException(ConflictException):
    message = "Username already exists"


class RoleCodeAlreadyExistsException(ConflictException):
    message = "Role with this code already exists"


class RoleInUseException(ConflictException):
    message = "Role is assigned to users and cannot be deleted"


class SystemRoleException(BadRequestException):
    message = "System role cannot be modified or deleted"


class PermissionNotFoundException(BadRequestException):
    message = "Unknown permission code"


class SelfBlockException(BadRequestException):
    message = "You cannot block yourself"


class BankScopeRequiredException(BadRequestException):
    message = "Bank employee must be linked to a bank"


# ---------- заявки ----------


class ApplicationNotEditableException(BadRequestException):
    message = "Application can be edited only in DRAFT status"

    def __init__(self, current_status: str | None = None, message: str | None = None):
        if message is None and current_status is not None:
            message = f"Application can be edited only in DRAFT status (current: {current_status})"
        super().__init__(message)


class InvalidStatusTransitionException(BadRequestException):
    message = "Invalid application status transition"


class ApplicationValidationException(BadRequestException):
    message = "Application is not ready for submission"
    example_missing = ["bank_id", "location.confirmed", "project.requested_amount"]

    def __init__(self, missing: list[str] | None = None, message: str | None = None):
        self.missing = missing or []
        if message is None and self.missing:
            message = (
                f"Application is not ready for submission: {len(self.missing)} field(s) missing"
            )
        super().__init__(message)


class BankSubjectTypeMismatchException(BadRequestException):
    message = "Selected bank does not work with this subject type"
    field = "bank_id"


class PhotoLimitExceededException(BadRequestException):
    message = "Maximum number of photos reached"
    field = "file"


class FounderNotFoundException(NotFoundException):
    message = "Founder not found in this application"


class FounderLimitExceededException(BadRequestException):
    message = "Maximum number of founders reached"
    field = "founders"


class FoundersNotAllowedException(BadRequestException):
    message = "Founders are specified only for MCHJ (LLC)"
    field = "founders"


class CompanyNotAllowedException(BadRequestException):
    message = "Company details are specified only for MCHJ (LLC)"
    field = "company"


class InvalidPhotoException(BadRequestException):
    message = "Only JPG, PNG and WEBP images are allowed"
    field = "file"


class PhotoTooLargeException(BadRequestException):
    message = "Photo is too large"
    field = "file"


class DocumentLimitExceededException(BadRequestException):
    message = "Maximum number of documents reached"
    field = "file"


class InvalidDocumentException(BadRequestException):
    message = "Only PDF and DOCX files are allowed"
    field = "file"


class DocumentTooLargeException(BadRequestException):
    message = "Document is too large"
    field = "file"


class LocationNotConfirmedException(BadRequestException):
    message = "Business location must be confirmed"
    field = "location.confirmed"


class LegalNameRequiredException(BadRequestException):
    message = "Legal name is required for this subject type"
    field = "legal_name"


class ScoringNotPendingException(BadRequestException):
    message = "Application is not waiting for scoring"


class BankDecisionAlreadyMadeException(BadRequestException):
    message = "Bank decision has already been recorded"


class RejectReasonRequiredException(BadRequestException):
    message = "Rejection reason is required"


class CouncilDecisionAlreadyMadeException(BadRequestException):
    message = "You have already voted on this application"


class NoCouncilMembersException(BadRequestException):
    message = "No active council members to assign"


class ResourceAllocationNotAllowedException(BadRequestException):
    message = "Resource allocation is allowed only after council approval"


# ---------- политика входа: YIA SSO только для заявителей ----------


class ApplicantLoginViaSSOException(ForbiddenException):
    message = "Applicants sign in via YIA Portal only"


class SSONotForInternalUsersException(ForbiddenException):
    message = (
        "YIA Portal sign-in is for applicants only. "
        "Internal users sign in with username and password"
    )


class SSOAccessDeniedException(ForbiddenException):
    message = "YIA Portal denied access: user is not allowed to sign in to this project"


class SSOInvalidStateException(BadRequestException):
    message = "Invalid SSO state, start sign-in again"


class ApplicantRoleNotAssignableException(BadRequestException):
    message = (
        "Applicant role is assigned automatically on YIA Portal sign-in and cannot be set manually"
    )


class ApplicantProfileIncompleteException(BadRequestException):
    """Профиль заявителя не дополнен: YIA SSO передаёт только Ф.И.О. и ПИНФЛ,
    остальное пользователь заполняет через PATCH /auth/me."""

    message = "Complete your profile before creating an application"
    example_missing = ["phone", "passport_number", "email"]

    def __init__(self, missing: list[str] | None = None, message: str | None = None):
        self.missing = missing or []
        if message is None and self.missing:
            message = "Complete your profile before creating an application: " + ", ".join(
                self.missing
            )
        super().__init__(message)
