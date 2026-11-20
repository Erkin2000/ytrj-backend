"""Минимальный клиент Telegram Bot API: опрос обновлений и скачивание фото.

Токен входит в URL запросов, поэтому URL нигде не логируется (логгер httpx
поднят до WARNING в configure_logging), а ошибки содержат только метод и описание.
"""

import httpx

from src.config import settings

# Long polling: Telegram держит запрос открытым до POLL_TIMEOUT секунд.
POLL_TIMEOUT = 25
ALLOWED_UPDATES = ["channel_post", "edited_channel_post"]


class TelegramError(Exception):
    def __init__(self, method: str, status: int, description: str):
        super().__init__(f"Telegram {method} failed ({status}): {description}")
        self.status = status


class TelegramClient:
    def __init__(self, token: str | None = None, api_url: str | None = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = (api_url or settings.TELEGRAM_API_URL).rstrip("/")
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(POLL_TIMEOUT + 15, connect=10))

    async def close(self) -> None:
        await self._http.aclose()

    async def call(self, method: str, **params) -> object:
        response = await self._http.post(f"{self.api_url}/bot{self.token}/{method}", json=params)
        try:
            body = response.json()
        except ValueError:
            raise TelegramError(method, response.status_code, "non-JSON response") from None
        if not body.get("ok"):
            raise TelegramError(method, response.status_code, str(body.get("description")))
        return body.get("result")

    async def get_me(self) -> dict:
        return await self.call("getMe")

    async def delete_webhook(self) -> None:
        # Опрос getUpdates не работает, пока у бота задан webhook.
        await self.call("deleteWebhook", drop_pending_updates=False)

    async def get_updates(self, offset: int | None) -> list[dict]:
        params = {"timeout": POLL_TIMEOUT, "allowed_updates": ALLOWED_UPDATES}
        if offset is not None:
            params["offset"] = offset
        return await self.call("getUpdates", **params)

    async def download_file(self, file_id: str) -> bytes:
        info = await self.call("getFile", file_id=file_id)
        file_path = info.get("file_path") if isinstance(info, dict) else None
        if not file_path:
            raise TelegramError("getFile", 200, "no file_path")
        response = await self._http.get(f"{self.api_url}/file/bot{self.token}/{file_path}")
        if response.status_code != 200:
            raise TelegramError("downloadFile", response.status_code, "download failed")
        return response.content
