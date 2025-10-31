from app.dao.base import BaseDAO
from app.habit.models import Habit


class HabitDAO(BaseDAO):
    model = Habit
