"""Telegram alert delivery for Project Sentinel."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib import parse, request, error


logger = logging.getLogger(__name__)


@dataclass
class TelegramAlertResult:
    """Result returned by a Telegram send operation."""

    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None


class TelegramAlertManager:
    """Minimal Telegram Bot API client for motion and startup alerts."""

    def __init__(self, bot_token: Optional[str], chat_id: Optional[str], enabled: bool = False, parse_mode: str = "HTML", bot_name: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.parse_mode = parse_mode
        self.bot_name = bot_name

    def is_configured(self) -> bool:
        return bool(self.enabled and self.bot_token and self.chat_id)

    def send_message(self, text: str) -> TelegramAlertResult:
        if not self.is_configured():
            return TelegramAlertResult(success=False, error_message="Telegram alerts are not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = parse.urlencode({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": "true",
        }).encode("utf-8")

        try:
            req = request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with request.urlopen(req, timeout=8) as response:
                response_body = response.read().decode("utf-8")
                parsed = json.loads(response_body) if response_body else {}
                if parsed.get("ok"):
                    return TelegramAlertResult(success=True, status_code=response.status)

                return TelegramAlertResult(
                    success=False,
                    status_code=response.status,
                    error_message=parsed.get("description", "Telegram API rejected the message"),
                )
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"Telegram HTTP error: {exc.code} {body}")
            return TelegramAlertResult(success=False, status_code=exc.code, error_message=body or str(exc))
        except Exception as exc:
            logger.error(f"Telegram send failed: {exc}")
            return TelegramAlertResult(success=False, error_message=str(exc))

    def send_startup_alert(self, app_name: str, host: str, port: int) -> TelegramAlertResult:
        bot_line = f"Bot: {self.bot_name}\n" if self.bot_name else ""
        message = (
            f"<b>{app_name}</b> started successfully\n"
            f"{bot_line}"
            f"Host: {host}:{port}\n"
            f"Time: {datetime.utcnow().isoformat()}Z"
        )
        return self.send_message(message)

    def send_shutdown_alert(self, app_name: str) -> TelegramAlertResult:
        message = f"<b>{app_name}</b> is shutting down\nTime: {datetime.utcnow().isoformat()}Z"
        return self.send_message(message)

    def send_motion_alert(
        self,
        camera_name: str,
        camera_id: int,
        timestamp: datetime,
        contour_count: int,
        max_contour_area: int,
    ) -> TelegramAlertResult:
        message = (
            f"<b>Motion detected</b>\n"
            f"Camera: {camera_name} (ID {camera_id})\n"
            f"Time: {timestamp.isoformat()}Z\n"
            f"Contours: {contour_count}\n"
            f"Max area: {max_contour_area}"
        )
        return self.send_message(message)