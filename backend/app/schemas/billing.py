from pydantic import BaseModel, Field


class BillingInfo(BaseModel):
    wallet_balance: int = Field(..., description="Current wallet balance in Toman")
    cost_per_connected: int = Field(..., description="Cost per connected call in Toman")
    currency: str = "Toman"
    disabled_by_dialer: bool = False


class BillingUpdate(BaseModel):
    wallet_balance: int | None = Field(default=None, description="New wallet balance in Toman")
    cost_per_connected: int | None = Field(default=None, description="New cost per connected call in Toman")
