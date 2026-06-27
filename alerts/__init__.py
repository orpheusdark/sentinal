"""Alerts module for Project Sentinel."""

from .telegram import TelegramAlertManager, TelegramAlertResult

__all__ = ["TelegramAlertManager", "TelegramAlertResult"]
