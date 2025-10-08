import httpx
import os
from dotenv import load_dotenv

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_BASE_URL = "https://api.paystack.co"


async def initialize_payment(email: str, amount: int, reference: str, metadata: dict = None):
    """
    Initialize Paystack payment

    Args:
        email: Customer email
        amount: Amount in kobo (multiply naira by 100)
        reference: Unique payment reference
        metadata: Additional payment metadata

    Returns:
        dict: Payment initialization result
    """
    try:
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "email": email,
            "amount": amount,
            "reference": reference,
            "callback_url": os.getenv("PAYSTACK_CALLBACK_URL", "https://fombinatower.com/booking/success"),
        }

        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                json=payload,
                headers=headers,
            )
            result = response.json()

            if result.get("status"):
                return {
                    "success": True,
                    "authorization_url": result["data"]["authorization_url"],
                    "access_code": result["data"]["access_code"],
                    "reference": result["data"]["reference"],
                }
            else:
                return {"success": False, "error": result.get("message", "Payment initialization failed")}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def verify_payment(reference: str):
    """
    Verify Paystack payment

    Args:
        reference: Payment reference

    Returns:
        dict: Payment verification result
    """
    try:
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                headers=headers,
            )
            result = response.json()

            if result.get("status") and result["data"]["status"] == "success":
                return {
                    "success": True,
                    "amount": result["data"]["amount"],
                    "customer": result["data"]["customer"],
                    "paid_at": result["data"]["paid_at"],
                    "reference": result["data"]["reference"],
                }
            else:
                return {"success": False, "error": "Payment verification failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
