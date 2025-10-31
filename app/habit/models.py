from sqlalchemy.orm import Mapped, mapped_column

from app.dao.database import Base


class Habit(Base):
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"
