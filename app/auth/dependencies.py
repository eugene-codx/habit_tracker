from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid

from datetime import datetime, UTC

from fastapi import Depends, HTTPException, Request, status
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dao import UsersDAO
from app.auth.models import User
from app.config import settings
from app.dao.session_maker import SessionDep
from app.exceptions import ForbiddenException, NoJwtException, NoUserIdException, TokenExpiredException, TokenNoFound


def get_token(request: Request):
    """Extracts the JWT token from the request headers or cookies.
    Raises:
        TokenNoFound: If no token is found in headers or cookies.
    """

    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            return token

    token = request.cookies.get("users_access_token")
    if not token:
        raise TokenNoFound
    return token


async def get_current_user(token: str = Depends(get_token), session: AsyncSession = SessionDep):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
    except JWTError as err:
        raise NoJwtException from err

    expire: str = payload.get("exp")
    expire_time = datetime.fromtimestamp(int(expire), tz=UTC)
    if (not expire) or (expire_time < datetime.now(UTC)):
        raise TokenExpiredException

    user_public_id: uuid.UUID = payload.get("sub")
    if not user_public_id:
        raise NoUserIdException

    user = await UsersDAO.find_one_or_none_by_public_id(data_public_id=user_public_id, session=session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_admin_user(current_user: User = Depends(get_current_user)):  # nosec # noqa: B008
    if current_user.role.id in [3, 4]:
        return current_user
    raise ForbiddenException
