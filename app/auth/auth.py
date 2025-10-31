import secrets
from datetime import datetime, timedelta, UTC

from loguru import logger
from jose import jwt
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Response

from app.auth.dao import UsersDAO
from app.auth.models import RefreshToken
from app.auth.schemas import TokenResponse
from app.auth.utils import verify_password
from app.config import settings
from app.dao.session_maker import SessionDep


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    # Append a unique identifier (jti) to prevent token collisions
    to_encode["jti"] = secrets.token_urlsafe(8)
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"Access token created for sub={data.get('sub')}, jti={to_encode['jti']}")
    return encode_jwt


def create_refresh_token() -> str:
    # Generate a secure random token for refresh
    return secrets.token_urlsafe(64)


async def authenticate_user(email_username: str, password: str, session: AsyncSession = SessionDep):
    if "@" in email_username:
        user = await UsersDAO.find_one_or_none(session=session, filters={"email": email_username})
    else:
        user = await UsersDAO.find_one_or_none(session=session, filters={"username": email_username})
    if not user or verify_password(plain_password=password, hashed_password=user.password) is False:
        logger.info(f"Failed login attempt: {email_username}")
        return None
    logger.info(f"User authenticated successfully: {email_username}")
    return user


# Functions for working with Refresh tokens
async def store_refresh_token(
    session: AsyncSession,
    user_id: int,
    token: str,
    request: Request | None = None,
    revoke_same_device: bool = True,
) -> RefreshToken:
    """Save a new refresh token to the database"""
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Extract client information for auditing (optional)
    user_agent = request.headers.get("user-agent") if request else None
    ip_address = request.client.host if request and request.client else None

    # If tokens for the same device should be revoked
    if revoke_same_device and user_agent:
        # Revoke all active tokens for this user and device
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.user_agent == user_agent,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )

        await session.execute(stmt)
        logger.info(f"Refresh tokens revoked for user_id={user_id}, user_agent={user_agent}")

    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    session.add(refresh_token)
    await session.commit()
    await session.refresh(refresh_token)
    logger.info(f"Refresh token saved for user_id={user_id}, user_agent={user_agent}, ip={ip_address}")
    return refresh_token


async def validate_refresh_token(session: AsyncSession, token: str) -> RefreshToken | None:
    """Validate a refresh token"""
    query = select(RefreshToken).where(
        RefreshToken.token == token,
        RefreshToken.is_revoked.is_(False),
        RefreshToken.expires_at > datetime.now(UTC),
    )
    result = await session.execute(query)
    valid = result.scalars().first()
    if not valid:
        logger.info("Refresh token is invalid or revoked")
    return valid


async def revoke_refresh_token(session: AsyncSession, token: str) -> bool:
    """Revoke a refresh token"""
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.token == token,
        )
        .values(
            is_revoked=True,
        )
    )

    result = await session.execute(stmt)
    await session.commit()
    if not result.rowcount > 0:
        logger.info("Refresh token not found for revocation")
    return result.rowcount > 0


async def set_auth_tokens(response: Response, request: Request, user_id: int, user_public_id: str, session):
    access_token = create_access_token({"sub": str(user_public_id)})
    refresh_token = create_refresh_token()

    # Save refresh token to the database
    await store_refresh_token(
        session=session,
        user_id=user_id,
        token=refresh_token,
        request=request,
    )

    response.set_cookie(
        key="users_access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="strict",
        secure=settings.TOKENS_COOKIE_SECURE,
    )
    response.set_cookie(
        key="users_refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="strict",
        secure=settings.TOKENS_COOKIE_SECURE,
    )
    logger.info(f"Auth cookies set for user_id={user_id}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def revoke_all_user_refresh_tokens(session: AsyncSession, user_id: int) -> int:
    """Revoke all tokens of a user (logout on all devices)"""
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        )
        .values(is_revoked=True)
    )

    result = await session.execute(stmt)
    await session.commit()
    logger.info(f"All refresh tokens revoked for user_id={user_id}")
    return result.rowcount


async def cleanup_expired_tokens(session: AsyncSession) -> int:
    """Remove expired tokens (for periodic cleanup)"""
    stmt = delete(RefreshToken).where(
        (RefreshToken.expires_at < datetime.now(UTC)) | (RefreshToken.is_revoked.is_(True)),
    )
    result = await session.execute(stmt)
    await session.commit()
    logger.info(f"Removed {result.rowcount} expired or revoked refresh tokens")
    return result.rowcount


async def get_active_session_tokens(session, user_id):
    query = (
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .order_by(RefreshToken.created_at.desc())
    )
    result = await session.execute(query)
    tokens = result.scalars().all()
    return tokens


async def get_active_sessions(session: AsyncSession, user_id: int) -> list[dict]:
    """Retrieve the list of a user's active sessions"""
    tokens = await get_active_session_tokens(session, user_id)
    logger.info(f"Retrieved {len(tokens)} active sessions for user_id={user_id}")

    return [
        {
            "id": token.id,
            "user_agent": token.user_agent,
            "ip_address": token.ip_address,
            "created_at": token.created_at,
            "expires_at": token.expires_at,
        }
        for token in tokens
    ]


async def revoke_session_by_id(session: AsyncSession, token_id: int, user_id: int) -> bool:
    """Revoke a session by token ID (with ownership check)"""
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.id == token_id,
            RefreshToken.user_id == user_id,
        )  # Verify token ownership
        .values(is_revoked=True)
    )

    result = await session.execute(stmt)
    await session.commit()
    if result.rowcount > 0:
        logger.info(f"Session token_id={token_id} revoked for user_id={user_id}")
    else:
        logger.info(f"Session token_id={token_id} for user_id={user_id} not found or already revoked")
    return result.rowcount > 0


async def limit_active_sessions(session: AsyncSession, user_id: int, max_sessions: int = 5) -> int:
    """Limit the number of a user's active sessions"""
    # Get all active tokens ordered from newest to oldest
    tokens = await get_active_session_tokens(session, user_id)

    # If the number of tokens exceeds the limit
    if len(tokens) > max_sessions:
        # Get the IDs of tokens to revoke (oldest first)
        tokens_to_revoke = tokens[max_sessions:]
        token_ids = [token.id for token in tokens_to_revoke]

        # Revoke excessive tokens
        stmt = (
            update(
                RefreshToken,
            )
            .where(
                RefreshToken.id.in_(token_ids),
            )
            .values(is_revoked=True)
        )

        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    return 0
