"""Heroku Platform API client for dyno management.

This module provides a client for interacting with the Heroku Platform API
to manage dyno scaling programmatically.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HerokuClient:
    """Client for Heroku Platform API dyno management.
    
    Uses the Heroku Formation API to scale dynos up/down.
    """

    BASE_URL = "https://api.heroku.com"

    def __init__(self, api_key: str, app_name: str) -> None:
        """Initialize Heroku client.
        
        Args:
            api_key: Heroku API key (from Account Settings)
            app_name: Heroku app name
        """
        self.api_key = api_key
        self.app_name = app_name
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.heroku+json; version=3",
            "Content-Type": "application/json",
        }

    async def get_dyno_quantity(self, dyno_type: str = "worker") -> int:
        """Get current dyno quantity for a process type.
        
        Args:
            dyno_type: Process type (e.g., "web", "worker")
            
        Returns:
            Number of dynos currently running
        """
        url = f"{self.BASE_URL}/apps/{self.app_name}/formation/{dyno_type}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self._headers)

                if response.status_code == 404:
                    # Process type doesn't exist yet
                    logger.warning("Process type '%s' not found", dyno_type)
                    return 0

                response.raise_for_status()
                data: dict[str, Any] = response.json()
                quantity = data.get("quantity", 0)
                logger.info("Current %s dyno quantity: %d", dyno_type, quantity)
                return quantity

            except httpx.HTTPError as e:
                logger.error("Failed to get dyno quantity: %s", e)
                raise

    async def scale_dyno(self, dyno_type: str = "worker", quantity: int = 1) -> bool:
        """Scale a dyno process to specified quantity.
        
        Args:
            dyno_type: Process type (e.g., "web", "worker")
            quantity: Number of dynos to scale to (0 to stop)
            
        Returns:
            True if scaling succeeded
        """
        url = f"{self.BASE_URL}/apps/{self.app_name}/formation"

        payload = {
            "updates": [
                {
                    "type": dyno_type,
                    "quantity": quantity,
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    url,
                    headers=self._headers,
                    json=payload
                )
                response.raise_for_status()

                logger.info(
                    "Scaled %s dyno to %d",
                    dyno_type,
                    quantity
                )
                return True

            except httpx.HTTPError as e:
                logger.error("Failed to scale dyno: %s", e)
                raise

    async def ensure_worker_running(self) -> bool:
        """Ensure worker dyno is running (scale to 1 if not).
        
        Returns:
            True if worker is now running
        """
        current = await self.get_dyno_quantity("worker")
        if current == 0:
            return await self.scale_dyno("worker", 1)
        return True

    async def stop_worker(self) -> bool:
        """Stop worker dyno (scale to 0).
        
        Returns:
            True if worker is now stopped
        """
        return await self.scale_dyno("worker", 0)
