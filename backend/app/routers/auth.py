from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import settings
from app.services import auth_service, email_service

router = APIRouter(prefix="/auth", tags=["Auth"])

_bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user: dict


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    """FastAPI dependency — inject this into any route that requires a
    logged-in user. Raises 401 if the token is missing, malformed, expired,
    references a user that no longer exists, OR was issued before the
    user's most recent password change (see token_still_valid)."""
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    try:
        decoded = auth_service.decode_access_token(credentials.credentials)
    except auth_service.InvalidToken:
        raise HTTPException(401, "Invalid or expired token")

    if not auth_service.token_still_valid(decoded["user_id"], decoded["pwd_ts"]):
        raise HTTPException(401, "Your password was changed — please sign in again")

    user = auth_service.get_user_by_id(decoded["user_id"])
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user


def require_verified_user(current_user: dict = Depends(get_current_user)) -> dict:
    """A stricter version of get_current_user for routes that do real
    work (uploading data, running analyses, exporting reports) — a
    logged-in-but-unverified account can still hit /auth/me and
    /auth/resend-verification (those use plain get_current_user), but is
    blocked from everything else until they verify. Without this
    distinction, an unverified account could use every feature
    indefinitely and verification would mean nothing."""
    if not current_user["is_verified"]:
        raise HTTPException(403, "Please verify your email before continuing")
    return current_user


def _send_verification_email(user: dict) -> None:
    token = auth_service.create_verification_token(user["id"])
    link = f"{settings.frontend_base_url}/verify-email?token={token}"
    email_service.send_email(
        user["email"],
        "Verify your StatScholar account",
        f"Welcome to StatScholar!\n\nVerify your email by visiting this link "
        f"(expires in 24 hours):\n\n{link}\n\nIf you didn't create this account, ignore this email.",
    )


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    try:
        user = auth_service.register_user(req.email, req.password)
    except auth_service.EmailAlreadyRegistered as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    _send_verification_email(user)

    token = auth_service.create_access_token(user["id"])
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    try:
        user = auth_service.authenticate_user(req.email, req.password)
    except auth_service.InvalidCredentials as e:
        raise HTTPException(401, str(e))

    token = auth_service.create_access_token(user["id"])
    return AuthResponse(access_token=token, user=user)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """Lists every registered account (id, email, signup date, verification
    status — never password hashes). Requires a valid login, so this isn't
    a public endpoint leaking every registered email to anyone who finds
    the URL. There's no separate 'admin' role in this app — any logged-in
    user can see this, which is fine for a single-developer/small-scale
    tool but worth tightening (to a real admin check) before a wider
    deployment."""
    return {"users": auth_service.list_users()}


@router.post("/resend-verification")
async def resend_verification(current_user: dict = Depends(get_current_user)):
    if current_user["is_verified"]:
        return {"message": "Already verified."}
    _send_verification_email(current_user)
    return {"message": "Verification email sent."}


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest):
    try:
        user = auth_service.verify_email_token(req.token)
    except auth_service.InvalidToken as e:
        raise HTTPException(400, str(e))
    return {"message": "Email verified.", "user": user}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Always returns the same generic response whether or not the email
    is registered — revealing that would let anyone probe which emails
    have accounts here (a classic account-enumeration issue)."""
    token = auth_service.create_password_reset_token(req.email)
    if token:
        link = f"{settings.frontend_base_url}/reset-password?token={token}"
        email_service.send_email(
            req.email,
            "Reset your StatScholar password",
            f"A password reset was requested for your StatScholar account.\n\n"
            f"Reset it by visiting this link (expires in 1 hour):\n\n{link}\n\n"
            f"If you didn't request this, ignore this email — your password won't change.",
        )
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    try:
        auth_service.reset_password(req.token, req.new_password)
    except auth_service.InvalidToken as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "Password reset successfully."}
