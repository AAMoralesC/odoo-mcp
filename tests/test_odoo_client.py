import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("ODOO_URL", "http://localhost:8069")
os.environ.setdefault("ODOO_DB", "odoo")
os.environ.setdefault("ODOO_USER", "admin")
os.environ.setdefault("ODOO_PASSWORD", "admin")
os.environ.setdefault("ALLOWED_MODELS", "res.partner,sale.order")

from odoo_mcp.config import load_config
from odoo_mcp.odoo_client import OdooClient


class TestOdooClient(unittest.TestCase):
    def _client(self):
        return OdooClient(load_config())

    @patch("odoo_mcp.odoo_client.xmlrpc.client.ServerProxy")
    def test_authenticate_success(self, proxy_cls):
        common = MagicMock()
        common.authenticate.return_value = 7
        proxy_cls.return_value = common
        client = self._client()
        self.assertEqual(client.authenticate(), 7)
        self.assertEqual(client.uid, 7)

    @patch("odoo_mcp.odoo_client.xmlrpc.client.ServerProxy")
    def test_authenticate_failure(self, proxy_cls):
        common = MagicMock()
        common.authenticate.return_value = False
        proxy_cls.return_value = common
        client = self._client()
        with self.assertRaises(PermissionError):
            client.authenticate()

    def test_list_allowed_models_sorted(self):
        client = self._client()
        self.assertEqual(client.list_allowed_models(), ["res.partner", "sale.order"])

    def test_disallowed_model_raises(self):
        client = self._client()
        with self.assertRaises(ValueError):
            client.search_read("account.move", [], None, 5)

    @patch("odoo_mcp.odoo_client.xmlrpc.client.ServerProxy")
    def test_search_read_calls_execute_kw(self, proxy_cls):
        common = MagicMock()
        common.authenticate.return_value = 7
        models = MagicMock()
        models.execute_kw.return_value = [{"id": 1, "name": "Acme"}]
        # ServerProxy se instancia dos veces: common y models
        proxy_cls.side_effect = [common, models]
        client = self._client()
        client.authenticate()
        result = client.search_read("res.partner", [["name", "ilike", "acme"]], ["name"], 5)
        self.assertEqual(result, [{"id": 1, "name": "Acme"}])
        models.execute_kw.assert_called_once()
        args = models.execute_kw.call_args.args
        self.assertEqual(args[3], "res.partner")
        self.assertEqual(args[4], "search_read")

    @patch("odoo_mcp.odoo_client.xmlrpc.client.ServerProxy")
    def test_read_missing_raises(self, proxy_cls):
        common = MagicMock()
        common.authenticate.return_value = 7
        models = MagicMock()
        models.execute_kw.return_value = []
        proxy_cls.side_effect = [common, models]
        client = self._client()
        client.authenticate()
        with self.assertRaises(LookupError):
            client.read("res.partner", 999)


if __name__ == "__main__":
    unittest.main()
