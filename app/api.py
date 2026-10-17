"""OsonTopshir hamkor API klienti (https://developers.osontopshir.uz)."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class PartnerError(Exception):
    def __init__(self, status: int, code: str, message: str = "", retry_after: float | None = None):
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        """5xx, 429 va tarmoq xatosi — qayta urinish mumkin. Qolgan 4xx — yo'q."""
        return self.status >= 500 or self.status == 429 or self.status == 0


class PartnerClient:
    def __init__(self, base: str, api_key: str, transport: httpx.AsyncBaseTransport | None = None):
        self._http = httpx.AsyncClient(
            base_url=base,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
            transport=transport,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, *, retries: int = 0, **kwargs) -> httpx.Response:
        for attempt in range(retries + 1):
            try:
                response = await self._http.request(method, path, **kwargs)
            except httpx.HTTPError as e:
                err = PartnerError(0, "network_error", str(e))
            else:
                if response.status_code < 400:
                    return response
                err = self._error(response)
            if not err.retryable or attempt == retries:
                raise err
            await asyncio.sleep(err.retry_after or 2 ** attempt)
        raise AssertionError("unreachable")

    @staticmethod
    def _error(response: httpx.Response) -> PartnerError:
        try:
            body = response.json().get("error", {})
        except Exception:
            body = {}
        retry = response.headers.get("Retry-After")
        return PartnerError(
            response.status_code,
            body.get("code") or "http_error",
            body.get("message") or response.text[:200],
            float(retry) if retry and retry.replace(".", "", 1).isdigit() else None,
        )

    async def credits(self) -> dict[str, dict]:
        data = (await self._request("GET", "/credits", retries=2)).json()
        return {b["service"]: b for b in data.get("balances", [])}

    async def create_order(self, service: str, params: dict, idempotency_key: str,
                           metadata: dict | None = None) -> dict:
        # Qayta urinish YO'Q: `Idempotency-Key` xavfsiz qiladi, lekin qaror (qachon qayta
        # urinish) chaqiruvchida — buyurtma navbati shuni boshqaradi.
        payload = {"service": service, "params": params}
        if metadata:
            payload["metadata"] = metadata
        response = await self._request(
            "POST", "/orders", json=payload, headers={"Idempotency-Key": idempotency_key}
        )
        return response.json()

    async def get_order(self, order_id: str) -> dict:
        return (await self._request("GET", f"/orders/{order_id}", retries=2)).json()

    async def cancel_order(self, order_id: str) -> dict:
        return (await self._request("POST", f"/orders/{order_id}/cancel")).json()

    async def download(self, file_id: str) -> bytes:
        response = await self._request("GET", f"/files/{file_id}/content", retries=2, follow_redirects=True)
        return response.content
