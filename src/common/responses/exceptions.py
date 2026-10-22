class ApiException(Exception):
    status_code = 400
    message = "Bad request"

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


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
    message = "Bank not found"


class ApplicationNotFoundException(NotFoundException):
    message = "Application not found"


class PhotoNotFoundException(NotFoundException):
    message = "Photo not found"


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


class InvalidStatusTransitionException(BadRequestException):
    message = "Invalid application status transition"


class ApplicationValidationException(BadRequestException):
    message = "Application is not ready for submission"

    def __init__(self, missing: list[str] | None = None, message: str | None = None):
        self.missing = missing or []
        super().__init__(message)


class BankSubjectTypeMismatchException(BadRequestException):
    message = "Selected bank does not work with this subject type"


class PhotoLimitExceededException(BadRequestException):
    message = "Maximum number of photos reached"


class InvalidPhotoException(BadRequestException):
    message = "Only JPG, PNG and WEBP images are allowed"


class PhotoTooLargeException(BadRequestException):
    message = "Photo is too large"


class LocationNotConfirmedException(BadRequestException):
    message = "Business location must be confirmed"


class LegalNameRequiredException(BadRequestException):
    message = "Legal name is required for this subject type"


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
