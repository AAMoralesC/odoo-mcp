"""Servidor MCP para Odoo (modo lectura)."""

from __future__ import annotations

import json
import sys

from mcp.server.fastmcp import FastMCP

from .config import load_config, Config
from .odoo_client import OdooClient

mcp = FastMCP("odoo-mcp")
_client: OdooClient | None = None


def _get_client() -> OdooClient:
    global _client
    if _client is None:
        _client = OdooClient(load_config())
    return _client


@mcp.tool()
def list_allowed_models() -> list[str]:
    """Lista los modelos de Odoo que este servidor permite consultar."""
    return _get_client().list_allowed_models()


@mcp.tool()
def search_records(
    model: str, domain: list | None = None, fields: list[str] | None = None, limit: int = 20
) -> str:
    """Busca registros en Odoo. domain es una lista de condiciones estilo Odoo, ej. [['name','ilike','acme']].

    Devuelve JSON con los registros encontrados (max 200)."""
    records = _get_client().search_read(model, domain, fields, limit)
    return json.dumps(records, ensure_ascii=False, default=str)


@mcp.tool()
def read_record(model: str, record_id: int, fields: list[str] | None = None) -> str:
    """Lee un registro de Odoo por su ID. Devuelve JSON."""
    record = _get_client().read(model, record_id, fields)
    return json.dumps(record, ensure_ascii=False, default=str)


def main() -> None:
    try:
        _get_client().authenticate()
    except Exception as exc:  # pragma: no cover - arranque
        print(f"Error de conexion a Odoo: {exc}", file=sys.stderr)
        raise SystemExit(1)
    mcp.run()


if __name__ == "__main__":
    main()
