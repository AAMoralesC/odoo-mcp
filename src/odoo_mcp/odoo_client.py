"""Cliente XML-RPC para Odoo. Solo lectura en esta version."""

from __future__ import annotations

import xmlrpc.client
from typing import Any

from .config import Config


class OdooClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._uid: int | None = None
        self._models: xmlrpc.client.ServerProxy | None = None

    def _common(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/common")

    def _models_proxy(self) -> xmlrpc.client.ServerProxy:
        if self._models is None:
            self._models = xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/object")
        return self._models

    def authenticate(self) -> int:
        uid = self._common().authenticate(
            self.config.db, self.config.user, self.config.password, {}
        )
        if not uid:
            raise PermissionError("Autenticacion fallida en Odoo (revisa usuario/clave/base)")
        self._uid = uid
        return uid

    @property
    def uid(self) -> int:
        if self._uid is None:
            return self.authenticate()
        return self._uid

    def _ensure_allowed(self, model: str) -> None:
        if model not in self.config.allowed_models:
            raise ValueError(f"Modelo no permitido: {model}")

    def list_allowed_models(self) -> list[str]:
        return sorted(self.config.allowed_models)

    def search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        fields: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        self._ensure_allowed(model)
        if limit < 1 or limit > 200:
            raise ValueError("limit debe estar entre 1 y 200")
        kwargs: dict[str, Any] = {"limit": limit}
        if fields:
            kwargs["fields"] = fields
        return self._models_proxy().execute_kw(
            self.config.db,
            self.uid,
            self.config.password,
            model,
            "search_read",
            [domain or []],
            kwargs,
        )

    def read(
        self, model: str, record_id: int, fields: list[str] | None = None
    ) -> dict[str, Any]:
        self._ensure_allowed(model)
        kwargs: dict[str, Any] = {}
        if fields:
            kwargs["fields"] = fields
        result = self._models_proxy().execute_kw(
            self.config.db,
            self.uid,
            self.config.password,
            model,
            "read",
            [[record_id]],
            kwargs,
        )
        if not result:
            raise LookupError(f"Registro {record_id} no encontrado en {model}")
        return result[0]
