from fastapi import APIRouter, Query, HTTPException
import requests
from src.logging_config import logger
from sentry_sdk import capture_exception
router = APIRouter()

@router.get("/api/v1/prices/necessities-price")
def get_necessities_prices(
        category=Query(None), commodity=Query(None)
):
    try:
        logger.info(f"Fetching necessities prices for category: {category}, commodity: {commodity}")
        response = requests.get(
            "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
            params={"CategoryName": category, "Name": commodity},
            timeout=10  # 加入 timeout 以防請求卡住
        )
        response.raise_for_status()  # 檢查 HTTP 狀態碼

        result = response.json()
        logger.info("Successfully fetched necessities prices data.")
        return result
    except requests.exceptions.Timeout as err:
        logger.error(f"Request timed out: {err}", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=504, detail="Request timed out while fetching prices data.")

    except requests.exceptions.RequestException as err:
        logger.error(f"Request failed: {err}", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=502, detail="Failed to fetch prices data due to an external API error.")

    except Exception as err:
        logger.error(f"Unexpected error: {err}", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")