from pydantic import BaseModel, Field, ConfigDict


class HabitsResponse(BaseModel):
    id: int = Field(description="ID habit")
    name: str = Field(description="Habit name")

    model_config = ConfigDict(from_attributes=True)
