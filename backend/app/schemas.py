from pydantic import BaseModel


class AnomalyStatusUpdate(BaseModel):
    status: str
