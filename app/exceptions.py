from fastapi import HTTPException, status

UserEmailAlreadyExistsException = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists"
)

UsernameAlreadyExistsException = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="A user with this username already exists"
)

IncorrectEmailOrPasswordException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
)

TokenExpiredException = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

TokenNoFound = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

NoJwtException = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token!")

NoUserIdException = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")

ForbiddenException = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions!")

NoRefreshTokenException = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")

NoValidRefreshTokenException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
)

NoSessionException = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or does not belong to the current user"
)

MaxSessionsException = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST, detail="The maximum number of sessions must be at least 1"
)
