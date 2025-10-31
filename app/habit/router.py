from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings
from app.dao.session_maker import SessionDep
from app.habit.dao import HabitDAO
from app.habit.schemas import HabitsResponse

router = APIRouter(prefix=f"/{settings.APP_TITLE_UUID}/habit", tags=["Habit"])


@router.get("/habits")
async def get_habits(
    session: AsyncSession = SessionDep, user_data: User = Depends(get_current_user)  # nosec # noqa B008
) -> list[HabitsResponse]:
    habits = await HabitDAO.find_all(session=session, filters=None)
    return [HabitsResponse.model_validate(habit) for habit in habits if habit.is_enabled]
