from pydantic import BaseModel, EmailStr, Field

from app.departments import Department


class RouteRequest(BaseModel):
    email: EmailStr = Field(..., description="Adres e-mail nadawcy (trafi do nagłówka Reply-To)")
    message: str = Field(..., min_length=1, max_length=10_000, description="Treść zgłoszenia")

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "jan.nowak@example.com", "message": "Nie działa mi komputer"}]
        }
    }


class RouteResponse(BaseModel):
    department: Department = Field(..., description="Wybrany dział")
    recipient: str = Field(..., description="Adres e-mail, na który wysłano zgłoszenie")
