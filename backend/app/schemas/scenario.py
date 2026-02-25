from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ScenarioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)
    cost_per_connected: int | None = Field(default=None, ge=0)
    is_active: bool = True


class ScenarioCreate(ScenarioBase):
    company_id: int


class ScenarioUpdate(BaseModel):
    display_name: str | None = None
    cost_per_connected: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ScenarioOut(ScenarioBase):
    id: int
    company_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ScenarioSimple(BaseModel):
    """Simplified scenario schema for dialer responses"""
    id: int
    name: str
    display_name: str

    class Config:
        from_attributes = True


class RegisterScenarioItem(BaseModel):
    """
    Minimal scenario shape accepted from dialer startup registration.
    Dialer must not control scenario activation state.
    """
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)


class RegisterScenariosRequest(BaseModel):
    """Request from dialer app to register available scenarios"""
    company: str
    scenarios: list[RegisterScenarioItem]
