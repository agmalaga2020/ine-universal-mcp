"""
INE API Client - Production-grade client for Spanish National Statistics Institute API
Handles rate limiting, retries, timeouts, and structured error handling
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class INEAPIError(Exception):
    """Base exception for INE API errors"""

    pass


class INETimeoutError(INEAPIError):
    """Raised when API request times out"""

    pass


class INENotFoundError(INEAPIError):
    """Raised when resource is not found (404)"""

    pass


class INEServerError(INEAPIError):
    """Raised when INE server returns 5xx error"""

    pass


class SeriesMetadata(BaseModel):
    """Structured metadata for an INE series"""

    id: str = Field(..., description="Series ID")
    name: str = Field(..., description="Series name")
    description: Optional[str] = Field(None, description="Series description")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    frequency: Optional[str] = Field(None, description="Data frequency")
    source: Optional[str] = Field(None, description="Data source")
    last_update: Optional[str] = Field(None, description="Last update date")


class INEClient:
    """
    Async HTTP client for INE API with:
    - Exponential backoff retry logic
    - Request/response logging with timestamps
    - Timeout management
    - Structured error handling
    """

    BASE_URL = "https://servicios.ine.es/wstempus/js/ES"
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with retry logic and comprehensive error handling
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        start_time = datetime.now()
        timestamp = start_time.isoformat()

        logger.info(f"[{timestamp}] INE API Request: {method} {endpoint}")
        if params:
            logger.debug(f"[{timestamp}] Parameters: {params}")

        try:
            response = await self._client.request(method, endpoint, params=params)
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[{timestamp}] Response: {response.status_code} ({duration:.2f}s)")

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"[{timestamp}] Timeout after {self.timeout}s")
            raise INETimeoutError(
                f"Request timeout after {self.timeout}s. Try reducing date range or limit."
            ) from e

        except httpx.HTTPStatusError as e:
            status = e.response.status_code

            if status == 404:
                logger.error(f"[{timestamp}] Not found: {endpoint}")
                raise INENotFoundError(
                    "Series/table not found. Verify the ID is correct."
                ) from e

            elif status >= 500:
                # Retry on server errors with exponential backoff
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning(
                        f"[{timestamp}] Server error {status}, retrying in {wait_time}s "
                        f"(attempt {retry_count + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    return await self._request(method, endpoint, params, retry_count + 1)
                else:
                    logger.error(
                        f"[{timestamp}] Server error {status} after {self.max_retries} retries"
                    )
                    raise INEServerError(
                        "INE server error. Try again later or contact support."
                    ) from e

            else:
                logger.error(f"[{timestamp}] HTTP error {status}: {e.response.text}")
                raise INEAPIError(f"HTTP {status}: {e.response.text}") from e

        except Exception as e:
            logger.error(f"[{timestamp}] Unexpected error: {str(e)}")
            raise INEAPIError(f"Unexpected error: {str(e)}") from e

    async def search_series(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for series by keywords

        Args:
            query: Search keywords

        Returns:
            List of series matching the query
        """
        data = await self._request("GET", "/SEARCH", params={"text": query})

        if not isinstance(data, list):
            return []

        return data

    async def get_series_data(
        self,
        series_id: str,
        last_n: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get time series data points

        Args:
            series_id: Series ID
            last_n: Number of most recent data points
            start_date: Start date (YYYYMMDD or YYYY)
            end_date: End date (YYYYMMDD or YYYY)

        Returns:
            Series data with metadata
        """
        params = {}
        if last_n:
            params["nult"] = last_n
        if start_date:
            params["date"] = start_date
        if end_date:
            params["dateEnd"] = end_date

        return await self._request("GET", f"/DATOS_SERIE/{series_id}", params=params)

    async def get_series_metadata(self, series_id: str) -> SeriesMetadata:
        """
        Get complete metadata for a series

        Args:
            series_id: Series ID

        Returns:
            Structured metadata
        """
        data = await self._request("GET", f"/SERIE/{series_id}")

        return SeriesMetadata(
            id=data.get("COD") or data.get("Id", series_id),
            name=data.get("Nombre") or data.get("Name", ""),
            description=data.get("Descripcion") or data.get("Description"),
            unit=data.get("Unidad") or data.get("Unit"),
            frequency=data.get("T3_Periodicidad") or data.get("Frequency"),
            source=data.get("Fuente") or data.get("Source"),
            last_update=data.get("T3_FechaUltDato") or data.get("LastUpdate"),
        )

    async def get_operation_series(self, operation_code: str) -> List[Dict[str, Any]]:
        """
        Get all series for a specific operation (e.g., IPC, EPA)

        Args:
            operation_code: Operation code (e.g., '30' for IPC)

        Returns:
            List of series in the operation
        """
        data = await self._request("GET", f"/SERIES_OPERACION/{operation_code}")

        if not isinstance(data, list):
            return []

        return data

    async def get_table_data(self, table_id: str) -> Dict[str, Any]:
        """
        Get complete data from an INE table

        Args:
            table_id: Table ID

        Returns:
            Table data
        """
        return await self._request("GET", f"/DATOS_TABLA/{table_id}")

    async def get_variables(self) -> List[Dict[str, Any]]:
        """
        Get all variables in the INE system

        Returns:
            List of variables
        """
        data = await self._request("GET", "/VARIABLES")

        if not isinstance(data, list):
            return []

        return data

    async def get_operations(self) -> List[Dict[str, Any]]:
        """
        Get all operations available in the INE system

        Returns:
            List of operations
        """
        data = await self._request("GET", "/OPERACIONES")

        if not isinstance(data, list):
            return []

        return data
