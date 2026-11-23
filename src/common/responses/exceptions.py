import re

# Человекочитаемые пояснения к незаполненным полям заявки / профиля (ключи
# совпадают с `missing` в сводке перед отправкой). Остальные поля — "Required".
REQUIRED_FIELD_MESSAGES: dict[str, str] = {
    "product_id": "Select a product that is published, open for applications and fits the subject type",
    "subject_type": "Select the subject type",
    "bank_id": "Select an active bank of the product that works with this subject type",
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
    "bank_ids": "Add at least one active bank",
    "stages": "Add at least one stage",
}


def _required_message(field: str) -> str:
    if field.startswith("fields."):
        return "Fill in this required field of the product form"
    if field.startswith("stages.") and field.endswith(".fields"):
        return "Add at least one field to this stage"
    if field.startswith("stages.") and field.endswith(".options"):
        return "Add at least two options to this choice field"
    return REQUIRED_FIELD_MESSAGES.get(field, "Required")


def missing_to_errors(missing: list[str]) -> list[dict]:
    return [{"field": field, "message": _required_message(field)} for field in missing]


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
    code = "sso_failed"
    message = "YIA Portal authentication failed. Please try again."


# ---------- 403 ----------


class ForbiddenException(ApiException):
    status_code = 403
    message = "Forbidden"


class PermissionDeniedException(ForbiddenException):
    message = "You do not have permission to perform this action"


class UserOutOfScopeException(ForbiddenException):
    message = "You can manage only regular staff of your own direction"


class PermissionsNotGrantableException(ForbiddenException):
    message = "You cannot grant permissions you do not have"
    field = "permissions"


class AdminManagementException(ForbiddenException):
    message = "Only Super Admin can manage administrators and administrator roles"


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


class PinflAlreadyExistsException(ConflictException):
    message = "User with this PINFL already exists"
    field = "pinfl"


class RoleCodeAlreadyExistsException(ConflictException):
    message = "Role with this code already exists"


class RoleNameAlreadyExistsException(ConflictException):
    message = "Role with this Russian name already exists"
    field = "translations"


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


class RoleRequiredException(BadRequestException):
    message = "Role is required"
    field = "role_id"


class DirectionAdminRoleException(BadRequestException):
    message = (
        "Direction admin must have a direction role (FUND_OPERATOR, BANK_EMPLOYEE, COUNCIL_MEMBER)"
    )
    field = "is_direction_admin"


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
    example_missing = ["bank_id", "fields.12", "applicant.phone"]

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


class InvalidPhotoException(BadRequestException):
    message = "Only JPG, PNG and WEBP images are allowed"
    field = "file"


class PhotoTooLargeException(BadRequestException):
    message = "Photo is too large"
    field = "file"


class InvalidDocumentException(BadRequestException):
    message = "Only PDF and DOCX files are allowed"
    field = "file"


class DocumentTooLargeException(BadRequestException):
    message = "Document is too large"
    field = "file"


class ScoringNotPendingException(BadRequestException):
    message = "Application is not waiting for scoring"


class BankDecisionAlreadyMadeException(BadRequestException):
    message = "Bank decision has already been recorded"


class RejectReasonRequiredException(BadRequestException):
    message = "Rejection reason is required"


class CouncilDecisionAlreadyMadeException(BadRequestException):
    message = "You have already voted on this application"


class NoCouncilMembersException(BadRequestException):
    message = (
        "No active council members with the decision right and a PINFL (needed for E-IMZO) "
        "to send the bulletin to"
    )


# ---------- продукты ----------


class ProductNotFoundException(NotFoundException):
    message = "Product not found"


class FaqNotFoundException(NotFoundException):
    message = "FAQ item not found"


class NewsNotFoundException(NotFoundException):
    message = "News item not found"


class NewsPhotoNotFoundException(NotFoundException):
    message = "News item has no photo"


class EventNotFoundException(NotFoundException):
    message = "Event not found"


class EventCalendarRangeException(BadRequestException):
    message = "Invalid calendar range"
    field = "date_to"


class AboutSectionNotFoundException(NotFoundException):
    message = "About section not found"


class SiteContactNotFoundException(NotFoundException):
    message = "Contact not found"


class TestimonialNotFoundException(NotFoundException):
    message = "Testimonial not found"


class TestimonialPhotoNotFoundException(NotFoundException):
    message = "Testimonial photo not found"


class SiteContactEmptyException(BadRequestException):
    message = "Contact needs a phone or an email"
    field = "phone"


class CouncilProfileNotFoundException(NotFoundException):
    message = "Council member card not found"


class LeadershipProfileNotFoundException(NotFoundException):
    message = "Leadership card not found"


class PersonPhotoNotFoundException(NotFoundException):
    message = "The card has no photo"


class EventPhotoNotFoundException(NotFoundException):
    message = "The event has no photo"


class NewsScheduleException(BadRequestException):
    message = "Invalid publication time"
    field = "publish_at"


class ProductCategoryNotFoundException(NotFoundException):
    message = "Product category not found"
    field = "category_id"


class ProductCategoryInactiveException(BadRequestException):
    message = "Product category is inactive and cannot be selected"
    field = "category_id"


class ProductCategoryInUseException(ConflictException):
    message = "Category has products and cannot be deleted; deactivate it or move the products"


class ProductStageNotFoundException(NotFoundException):
    message = "Stage not found in this product"


class ProductFieldNotFoundException(NotFoundException):
    message = "Field not found in this product"


class ProductLockedException(ConflictException):
    message = (
        "Product already has applications: stages and fields cannot be changed. "
        "Copy the product to change its form"
    )


class ProductInUseException(ConflictException):
    message = "Product already has applications and cannot be deleted; archive it instead"


class StageNumberTakenException(ConflictException):
    message = "Stage with this number already exists in the product"
    field = "number"


class ProductNotReadyException(BadRequestException):
    message = "Product is not ready for publishing"
    example_missing = ["bank_ids", "stages"]

    def __init__(self, missing: list[str] | None = None, message: str | None = None):
        self.missing = missing or []
        super().__init__(message)


class ProductStatusException(BadRequestException):
    message = "Action is not allowed in the current product status"


class ProductNotAvailableException(BadRequestException):
    message = (
        "Product is not available: it is not published, out of the acceptance period "
        "or not intended for this subject type"
    )
    field = "product_id"


class BankNotInProductException(BadRequestException):
    message = "Selected bank does not work with this product"
    field = "bank_id"


class FieldValueInvalidException(BadRequestException):
    message = "Invalid field values"


class FileFieldException(BadRequestException):
    message = "Files are uploaded only to PHOTO and FILE fields; values are not set for them"


class FieldFileLimitExceededException(BadRequestException):
    message = "Maximum number of files for this field reached"
    field = "file"


class FieldFileNotFoundException(NotFoundException):
    message = "File not found in this field"


# ---------- поля с вариантами и условный показ ----------


class ProductFieldOptionNotFoundException(NotFoundException):
    message = "Option not found in this product"


class FieldOptionsException(BadRequestException):
    message = "Options are allowed only for SELECT, RADIO and CHECKBOX fields"
    field = "options"


class FieldConditionException(BadRequestException):
    message = "Invalid visibility condition"
    example_errors = [
        {
            "field": "visible_when",
            "message": "Controlling field must be a SELECT, RADIO or CHECKBOX field "
            "placed earlier in the form",
        }
    ]


class FieldInUseByConditionException(ConflictException):
    message = (
        "This field or option controls visibility of other fields or stages; "
        "remove those conditions first"
    )


class StageHiddenException(BadRequestException):
    message = "Stage is hidden by the current selection and cannot be filled in"


class FieldHiddenException(BadRequestException):
    message = "Field is hidden by the current selection"


# ---------- политика входа: YIA SSO только для заявителей ----------


class ApplicantLoginViaSSOException(ForbiddenException):
    message = "Applicants sign in via YIA Portal only"


class SSOAccessDeniedException(ForbiddenException):
    code = "sso_access_denied"
    message = "YIA Portal denied access: user is not allowed to sign in to this project"


class SSOInvalidStateException(BadRequestException):
    code = "sso_invalid_state"
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


# ---------- E-IMZO (ЭЦП) ----------


class EimzoException(UnauthorizedException):
    code = "eimzo_failed"
    message = "E-IMZO verification failed. Please try again."


class EimzoInvalidCodeException(BadRequestException):
    code = "eimzo_invalid_code"
    field = "code"
    message = "E-IMZO code is invalid, expired or already used. Sign with the key again."


class EimzoLoginNotAllowedException(ForbiddenException):
    code = "eimzo_login_not_allowed"
    message = "E-IMZO sign-in is available only for council members registered by the Super Admin"


class CouncilLoginViaEimzoException(ForbiddenException):
    code = "council_login_via_eimzo"
    message = "Council members sign in only with an E-IMZO key"


class EimzoSignerMismatchException(ForbiddenException):
    code = "eimzo_signer_mismatch"
    message = "The E-IMZO key belongs to another person: sign with your own key"


# ---------- бюллетени Совета ----------


class BulletinNotFoundException(NotFoundException):
    message = "Bulletin not found"


class BulletinFileNotFoundException(NotFoundException):
    message = "Bulletin has no attached file"


class BulletinNotEditableException(BadRequestException):
    message = (
        "Only a pending bulletin can be changed; after sending only the signing deadline "
        "can be extended"
    )


class BulletinStatusException(BadRequestException):
    message = "This action is not available in the current bulletin status"


class BulletinScheduleException(BadRequestException):
    message = "Invalid bulletin dates"
    field = "deadline_at"


class BulletinApplicationException(BadRequestException):
    message = "Only an application under Fund review can be attached to a bulletin"
    field = "application_id"


class BulletinNotViewedException(BadRequestException):
    message = "Open the bulletin before signing"


class BulletinFileNotViewedException(BadRequestException):
    message = "Open the attached file before signing"


class BulletinAlreadySignedException(BadRequestException):
    message = "You have already signed this bulletin"


class BulletinDeadlinePassedException(BadRequestException):
    message = "The signing deadline has passed"


class BulletinNotOpenForSigningException(BadRequestException):
    message = "The bulletin is not open for signing"
