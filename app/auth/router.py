from fastapi import APIRouter, Body, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import (
    authenticate_user,
    cleanup_expired_tokens,
    get_active_sessions,
    limit_active_sessions,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
    revoke_session_by_id,
    set_auth_tokens,
    validate_refresh_token,
)
from app.auth.dao import UsersDAO
from app.auth.dependencies import get_current_admin_user, get_current_user
from app.auth.models import User
from app.auth.schemas import RefreshTokenBody, SUserAddDB, SUserAuth, SUserInfo, SUserRegister, TokenResponse
from app.config import settings
from app.constants.messages import (
    CLEANUP_EXPIRED_TOKENS_MESSAGE,
    LOGOUT_SUCCESS_MESSAGE,
    REGISTER_SUCCESS_MESSAGE,
    SESSION_LIMIT_APPLIED_SUCCESS_MESSAGE,
    SESSION_SUCCESS_REVOKED_MESSAGE,
)
from app.dao.session_maker import SessionDep, TransactionSessionDep
from app.exceptions import (
    IncorrectEmailOrPasswordException,
    MaxSessionsException,
    NoRefreshTokenException,
    NoSessionException,
    NoValidRefreshTokenException,
    UserEmailAlreadyExistsException,
    UsernameAlreadyExistsException,
)

router = APIRouter(prefix=f"/{settings.APP_TITLE_UUID}/auth", tags=["Auth"])


@router.post("/register")
async def register_user(user_data: SUserRegister, session: AsyncSession = TransactionSessionDep) -> dict[str, str]:
    existing_user = await UsersDAO.find_one_or_none(session=session, filters=[{"username": user_data.username}])
    if existing_user:
        raise UsernameAlreadyExistsException

    existing_email = await UsersDAO.find_one_or_none(session=session, filters=[{"email": user_data.email}])
    if existing_email:
        raise UserEmailAlreadyExistsException

    user_data_dict = user_data.model_dump(exclude={"confirm_password"})
    await UsersDAO.add(session=session, values=SUserAddDB(**user_data_dict))
    return {"message": REGISTER_SUCCESS_MESSAGE}


@router.post("/login", response_model=TokenResponse)
async def auth_user(request: Request, response: Response, user_data: SUserAuth, session: AsyncSession = SessionDep):
    user = await authenticate_user(
        session=session, email_username=user_data.email_username, password=user_data.password
    )
    if user is None:
        raise IncorrectEmailOrPasswordException

    # Generate and set authentication tokens
    return await set_auth_tokens(
        response=response, request=request, user_public_id=user.public_id, user_id=user.id, session=session
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    session: AsyncSession = SessionDep,
    refresh_token: str = Cookie(None, alias="users_refresh_token"),
    refresh_token_body: RefreshTokenBody | None = Body(None),  # nosec # noqa B008
):
    """Token refresh using Refresh Token"""
    # Use token from cookies or from the body of the request
    token_to_use = (refresh_token_body.token if refresh_token_body else None) or refresh_token

    if not token_to_use:
        raise NoRefreshTokenException

    # Validate the refresh token
    stored_token = await validate_refresh_token(session, token_to_use)
    if not stored_token:
        raise NoValidRefreshTokenException

    # Check if the user associated with the token exists
    user = await UsersDAO.find_one_or_none(session=session, filters=[{"id": stored_token.user_id}])
    if user.id != stored_token.user_id:
        raise NoValidRefreshTokenException

    # Revoke the used refresh token
    await revoke_refresh_token(session, token_to_use)

    # Generate new tokens
    return await set_auth_tokens(
        response=response,
        request=request,
        user_id=stored_token.user_id,
        user_public_id=user.public_id,
        session=session,
    )


@router.post("/logout")
async def logout_user(
    response: Response,
    session: AsyncSession = SessionDep,
    user: User = Depends(get_current_user),  # nosec # noqa: B008
    refresh_token: str = Cookie(None, alias="users_refresh_token"),
    all_devices: bool = Body(False, embed=True),
):
    """
    Logout (token revocation).
    Allows the user to log out by revoking the refresh token(s) and deleting cookies.
    body:
        all_devices (bool): If True — logout from all devices, otherwise only from the current one.
    """
    if all_devices:
        # Revoke all user tokens (logout from all devices)
        await revoke_all_user_refresh_tokens(session, user.id)
    elif refresh_token:
        # Revoke only the specified refresh token
        await revoke_refresh_token(session, refresh_token)

    # Remove tokens from cookies
    response.delete_cookie(key="users_access_token")
    response.delete_cookie(key="users_refresh_token")

    return {"message": LOGOUT_SUCCESS_MESSAGE}


@router.get("/sessions")
async def list_active_sessions(
    session: AsyncSession = SessionDep, user: User = Depends(get_current_user)  # nosec # noqa B008
):
    """Get a list of the user's active sessions"""
    sessions = await get_active_sessions(session, user.id)
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int, session: AsyncSession = SessionDep, user: User = Depends(get_current_user)  # nosec # noqa B008
):
    """Revoke a specific session by ID"""
    success = await revoke_session_by_id(session, session_id, user.id)
    if not success:
        raise NoSessionException
    return {"message": SESSION_SUCCESS_REVOKED_MESSAGE}


@router.post("/sessions/limit")
async def limit_sessions(
    max_sessions: int = Body(..., embed=True),
    session: AsyncSession = SessionDep,
    user: User = Depends(get_current_user),  # nosec # noqa: B008
):
    """Limit the number of user's active sessions"""
    if max_sessions < 1:
        raise MaxSessionsException

    count = await limit_active_sessions(
        session,
        user.id,
        max_sessions,
    )
    return {"message": SESSION_LIMIT_APPLIED_SUCCESS_MESSAGE, "count": count}


@router.get("/me")
async def get_me(user_data: User = Depends(get_current_user)) -> SUserInfo:  # nosec # noqa: B008
    return SUserInfo.model_validate(user_data)


@router.get("/all_users")
async def get_all_users(
    session: AsyncSession = SessionDep, user_data: User = Depends(get_current_admin_user)  # nosec # noqa B008
) -> list[SUserInfo]:
    users = await UsersDAO.find_all(session=session, filters=None)
    return [SUserInfo.model_validate(user) for user in users]


@router.post("/cleanup_expired_tokens")
async def cleanup_expired_tokens_route(
    session: AsyncSession = SessionDep, user_data: User = Depends(get_current_admin_user)  # nosec # noqa B008
):
    count = await cleanup_expired_tokens(session=session)
    return {"message": CLEANUP_EXPIRED_TOKENS_MESSAGE, "count": count}
