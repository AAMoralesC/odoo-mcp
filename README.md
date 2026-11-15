# odoo-mcp

[![tests](https://github.com/AAMoralesC/odoo-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/AAMoralesC/odoo-mcp/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

> **Servidor MCP que expone el ORM de Odoo a agentes de IA.** Pregúntale a tu agente
> "¿cuántas facturas vencidas tiene el cliente X?" y que lo resuelva solo, sin abrir Odoo.

Combina dos cosas que casi nadie tiene juntas: **Odoo en producción** (17/18/19) y **agentes de IA**
(AI Agent Manager, AIAM™). El servidor se conecta a una instancia de Odoo por XML-RPC y
expone herramientas de lectura (y, más adelante, escritura con confirmación) a cualquier
agente compatible con MCP (Claude, OpenCode, Cursor, etc.).

---

## 🧠 Cómo funciona

```
Agente (Claude/OpenCode)  --MCP-->  odoo-mcp  --XML-RPC-->  Odoo
```

El agente ve tres herramientas:

| Herramienta | Qué hace |
|---|---|
| `list_allowed_models` | Modelos que el servidor permite consultar |
| `search_records` | Busca registros con filtros estilo Odoo (`domain`) |
| `read_record` | Lee un registro por ID |

Por defecto **solo lectura**. La escritura llegará con confirmación explícita.

---

## 🔒 Seguridad (importante)

- Solo se exponen los modelos listados en `ALLOWED_MODELS`. Por defecto: partners, usuarios, empresa, ventas, facturas, productos, proyectos y tareas.
- Usa un **usuario de Odoo con permisos mínimos** (no admin) y una instancia de prueba, nunca producción.
- Las credenciales viven en `.env`, que está en `.gitignore`.

---

## 📦 Instalación

```bash
git clone https://github.com/AAMoralesC/odoo-mcp.git
cd odoo-mcp
python -m venv .venv && . .venv/bin/activate
pip install -e .
cp .env.example .env   # edita con tus datos de Odoo
```

## 🐳 Levantar Odoo de prueba

```bash
docker compose up -d
```

Abre http://localhost:8069, crea la base `odoo` con usuario `admin` / clave `admin`.

## ▶️ Ejecutar el servidor

```bash
odoo-mcp
# o: python -m odoo_mcp
```

## 🔌 Conectarlo a tu agente

El repo incluye un `opencode.json` listo para OpenCode: abre el proyecto en OpenCode y el
servidor MCP de Odoo aparece automáticamente (requiere el venv creado con `pip install -e .`).

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "odoo-mcp",
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "odoo",
        "ODOO_USER": "admin",
        "ODOO_PASSWORD": "admin",
        "ALLOWED_MODELS": "res.partner,sale.order,account.move"
      }
    }
  }
}
```

Después le puedes preguntar: *"¿Cuántas facturas vencidas hay y de qué clientes?"*

---

## 🛠️ Desarrollo

```bash
pip install -e .
python -m unittest discover -s tests -v
```

## 🗺️ Roadmap

- [x] Lectura: list/search/read con allowlist
- [ ] Escritura con confirmación (`create_record`, `update_record`)
- [ ] Auditoría de acciones del agente
- [ ] Recursos MCP (schema de modelos)
- [ ] Publicación en PyPI

## 📄 Licencia

MIT — ver [LICENSE](./LICENSE).
