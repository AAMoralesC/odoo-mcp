"""Configuracion cargada desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    url: str
    db: str
    user: str
    password: str
    allowed_models: frozenset[str]
    writable_models: frozenset[str]


def load_config() -> Config:
    url = os.getenv("ODOO_URL", "").strip()
    db = os.getenv("ODOO_DB", "").strip()
    user = os.getenv("ODOO_USER", "").strip()
    password = os.getenv("ODOO_PASSWORD", "")
    raw_models = os.getenv("ALLOWED_MODELS", "")

    missing = [name for name, value in (("ODOO_URL", url), ("ODOO_DB", db), ("ODOO_USER", user)) if not value]
    if missing:
        raise ValueError(f"Faltan variables de entorno: {', '.join(missing)}")
    if not password:
        raise ValueError("Falta ODOO_PASSWORD")

    models = frozenset(m.strip() for m in raw_models.split(",") if m.strip())
    if not models:
        raise ValueError("ALLOWED_MODELS no puede estar vacio")

    raw_writable = os.getenv("WRITABLE_MODELS", "")
    writable = frozenset(m.strip() for m in raw_writable.split(",") if m.strip())
    # la escritura solo puede ser subconjunto de la lectura
    writable = writable & models

    return Config(url=url, db=db, user=user, password=password, allowed_models=models, writable_models=writable)
