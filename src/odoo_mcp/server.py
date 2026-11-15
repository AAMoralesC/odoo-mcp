"""Servidor MCP para Odoo. Lectura siempre; escritura solo con confirmacion explicita."""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid

logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("mcp.server").setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .odoo_client import OdooClient

mcp = FastMCP("odoo-mcp")
_client: OdooClient | None = None

# Acciones pendientes de confirmacion. Viven en memoria del proceso.
_PENDING: dict[str, dict] = {}
_TTL_SECONDS = 300
_MAX_PENDING = 20


def _get_client() -> OdooClient:
    global _client
    if _client is None:
        _client = OdooClient(load_config())
    return _client


def _purge_expired() -> None:
    now = time.time()
    for aid in [k for k, v in _PENDING.items() if v["expires_at"] < now]:
        del _PENDING[aid]


@mcp.tool()
def list_allowed_models() -> list[str]:
    """Lista los modelos de Odoo que este servidor permite consultar."""
    return _get_client().list_allowed_models()


@mcp.tool()
def list_writable_models() -> list[str]:
    """Lista los modelos de Odoo en los que se permite escribir (con confirmacion)."""
    return sorted(_get_client().config.writable_models)


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


@mcp.tool()
def propose_create(model: str, values: str) -> str:
    """Propone crear un registro en Odoo. NO escribe nada todavia.

    values debe ser un JSON con los campos, ej. '{"name":"Acme","email":"a@b.com"}'.
    Devuelve un action_id y una vista previa. Para ejecutar, llama a confirm_action(action_id)
    SOLO despues de que el usuario confirme explicitamente."""
    _purge_expired()
    if len(_PENDING) >= _MAX_PENDING:
        return json.dumps({"error": "Demasiadas acciones pendientes, cancela alguna primero"})
    try:
        parsed = json.loads(values)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"values no es JSON valido: {exc}"})
    if not isinstance(parsed, dict) or not parsed:
        return json.dumps({"error": "values debe ser un objeto JSON no vacio"})

    try:
        _get_client()._ensure_allowed(model)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    if model not in _get_client().config.writable_models:
        return json.dumps({"error": f"Escritura no permitida para el modelo: {model}. Revisa WRITABLE_MODELS."})

    action_id = str(uuid.uuid4())
    _PENDING[action_id] = {
        "kind": "create",
        "model": model,
        "record_id": None,
        "values": parsed,
        "preview": {"se creara": parsed},
        "created_at": time.time(),
        "expires_at": time.time() + _TTL_SECONDS,
    }
    return json.dumps(
        {
            "action_id": action_id,
            "accion": "crear",
            "modelo": model,
            "vista_previa": parsed,
            "expira_en_segundos": _TTL_SECONDS,
            "siguiente_paso": "Muestra la vista previa al usuario y llama a confirm_action(action_id) solo si confirma.",
        },
        ensure_ascii=False,
    )


@mcp.tool()
def propose_update(model: str, record_id: int, values: str) -> str:
    """Propone actualizar un registro de Odoo. NO escribe nada todavia.

    values debe ser un JSON con los campos a cambiar, ej. '{"email":"nuevo@b.com"}'.
    Lee el registro actual para mostrar el antes/despues. Para ejecutar, llama a
    confirm_action(action_id) SOLO despues de que el usuario confirme explicitamente."""
    _purge_expired()
    if len(_PENDING) >= _MAX_PENDING:
        return json.dumps({"error": "Demasiadas acciones pendientes, cancela alguna primero"})
    try:
        parsed = json.loads(values)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"values no es JSON valido: {exc}"})
    if not isinstance(parsed, dict) or not parsed:
        return json.dumps({"error": "values debe ser un objeto JSON no vacio"})

    try:
        before = _get_client().read(model, record_id, list(parsed.keys()))
    except (ValueError, LookupError, PermissionError) as exc:
        return json.dumps({"error": str(exc)})

    if model not in _get_client().config.writable_models:
        return json.dumps({"error": f"Escritura no permitida para el modelo: {model}. Revisa WRITABLE_MODELS."})

    action_id = str(uuid.uuid4())
    _PENDING[action_id] = {
        "kind": "update",
        "model": model,
        "record_id": record_id,
        "values": parsed,
        "preview": {"antes": before, "despues": parsed},
        "created_at": time.time(),
        "expires_at": time.time() + _TTL_SECONDS,
    }
    return json.dumps(
        {
            "action_id": action_id,
            "accion": "actualizar",
            "modelo": model,
            "id": record_id,
            "vista_previa": {"antes": before, "despues": parsed},
            "expira_en_segundos": _TTL_SECONDS,
            "siguiente_paso": "Muestra la vista previa al usuario y llama a confirm_action(action_id) solo si confirma.",
        },
        ensure_ascii=False,
    )


@mcp.tool()
def confirm_action(action_id: str) -> str:
    """Ejecuta una accion previamente propuesta (propose_create / propose_update).

    Solo llamar despues de que el usuario haya confirmado explicitamente la vista previa.
    La accion expira a los 5 minutos."""
    _purge_expired()
    action = _PENDING.get(action_id)
    if not action:
        return json.dumps({"error": "Accion no encontrada o expirada. Vuelve a proponerla."})

    client = _get_client()
    try:
        if action["kind"] == "create":
            new_id = client.create(action["model"], action["values"])
            result = {"creado": True, "modelo": action["model"], "id": new_id}
        else:
            updated = client.update(action["model"], action["record_id"], action["values"])
            result = {"actualizado": True, "modelo": action["model"], "id": action["record_id"], "registro": updated}
    except (ValueError, PermissionError, RuntimeError, Exception) as exc:
        return json.dumps({"error": f"No se pudo ejecutar: {exc}"})

    del _PENDING[action_id]
    _audit(action, result)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def cancel_action(action_id: str) -> str:
    """Cancela una accion pendiente sin ejecutarla."""
    if action_id in _PENDING:
        del _PENDING[action_id]
        return json.dumps({"cancelada": True, "action_id": action_id})
    return json.dumps({"error": "Accion no encontrada (ya ejecutada o expirada)"})


@mcp.tool()
def list_pending_actions() -> str:
    """Lista las acciones pendientes de confirmacion."""
    _purge_expired()
    return json.dumps(
        [
            {"action_id": aid, "accion": a["kind"], "modelo": a["model"], "expira_en": int(a["expires_at"] - time.time())}
            for aid, a in _PENDING.items()
        ],
        ensure_ascii=False,
    )


def _audit(action: dict, result: dict) -> None:
    import datetime

    line = (
        f"[AUDIT] {datetime.datetime.now().isoformat()} "
        f"accion={action['kind']} modelo={action['model']} "
        f"valores={json.dumps(action['values'], ensure_ascii=False)} resultado={json.dumps(result, ensure_ascii=False, default=str)}"
    )
    print(line, file=sys.stderr, flush=True)


def main() -> None:
    try:
        _get_client().authenticate()
    except Exception as exc:
        print(f"Error de conexion a Odoo: {exc}", file=sys.stderr)
        raise SystemExit(1)
    mcp.run()


if __name__ == "__main__":
    main()
