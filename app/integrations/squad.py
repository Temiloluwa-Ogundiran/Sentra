import httpx

from app.core.config import settings


class SquadClient:
    def __init__(self) -> None:
        self.base_url = settings.squad_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.squad_secret_key}",
            "Content-Type": "application/json",
        }

    async def create_credit_checkout(
        self,
        customer_email: str,
        amount_kobo: int,
        credits_to_add: int,
        user_id: int | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/transaction/initiate",
                json={
                    "email": customer_email,
                    "amount": amount_kobo,
                    "metadata": {
                        "purpose": "credit_recharge",
                        "credits_to_add": credits_to_add,
                        "user_id": user_id,
                    },
                },
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
