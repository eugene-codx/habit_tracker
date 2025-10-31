import uuid
from typing import Self

from pydantic import BaseModel, computed_field, ConfigDict, EmailStr, Field, model_validator

from app.auth.utils import get_password_hash


class UserBase(BaseModel):
    email: EmailStr = Field(description="Email")
    username: str = Field(
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Username (Latin letters, digits, _ . - only)",
    )

    model_config = ConfigDict(from_attributes=True)


class SUserRegister(UserBase):
    first_name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="First name, 3 to 100 characters",
    )
    password: str = Field(min_length=5, max_length=50, description="Password between 5 and 50 characters")
    confirm_password: str = Field(min_length=5, max_length=50, description="Repeat the password")

    @model_validator(mode="after")
    def check_password(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        self.password = get_password_hash(self.password)  # hash the password before saving to the database
        return self


class SUserAddDB(UserBase):
    first_name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="First name, 3 to 100 characters",
    )
    password: str = Field(min_length=5, description="Password as a HASH string")


class SUserAuth(BaseModel):
    email_username: EmailStr | str
    password: str = Field(min_length=5, max_length=50, description="Password between 5 and 50 characters")


class RoleModel(BaseModel):
    id: int = Field(description="Role ID")
    name: str = Field(description="Role name")
    model_config = ConfigDict(from_attributes=True)


class SUserInfo(UserBase):
    id: int | None = Field(exclude=True, default=None)  # Explicitly define and exclude
    public_id: uuid.UUID = Field(description="User PUBLIC_ID")
    first_name: str | None = Field(min_length=3, max_length=50, description="First name, 3 to 50 characters")
    role: RoleModel = Field(exclude=True)

    @computed_field
    def role_name(self) -> str:
        return self.role.name

    @computed_field
    def role_id(self) -> int:
        return self.role.id


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshTokenBody(BaseModel):
    token: str
