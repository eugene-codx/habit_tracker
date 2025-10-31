import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func, text, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.dao.database import Base


class Role(Base):
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="role")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"


class User(Base):
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password: Mapped[str]
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), default=1, server_default=text("1"))
    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="joined")
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        index=True,
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"


class RefreshToken(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(default=False)
    user_agent: Mapped[str] = mapped_column(nullable=True)
    ip_address: Mapped[str] = mapped_column(nullable=True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"
