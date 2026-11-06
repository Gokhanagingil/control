"""Compatibility and scope of the architecture response for signed-in users."""
import unittest
from unittest.mock import Mock, patch

import grc_plus


class ArchitectureMetadataTests(unittest.TestCase):
    def test_architecture_describes_domain_and_access_profiles(self):
        handler = Mock(path="/api/architecture/data")
        handler.respond.return_value = None
        with patch("app.DB", ":memory:"):
            self.assertTrue(grc_plus.get(handler))
        handler.respond.assert_called_once()
        status, data = handler.respond.call_args.args
        self.assertEqual(status, 200)
        self.assertTrue(data["note"])
        models = {model["id"]: model for model in data["models"]}
        self.assertEqual(len(models), len(data["models"]))
        self.assertTrue({"sources","mcp","controls","evidence","outcomes","audits","risks","access"} <= models.keys())
        for model in models.values():
            self.assertTrue(model["label"])
            self.assertTrue(model["items"])
            self.assertTrue(all(isinstance(item,str) and item for item in model["items"]))
        for key, terms in (
            ("audits", ("standart","madde","kapanış","kontrol")),
            ("risks", ("risk kataloğu","değerlendirme","karar")),
            ("access", ("entra","mfa","pilot","yerel")),
            ("mcp", ("api anahtarı","kanıt")),
        ):
            with self.subTest(model=key):
                description = " ".join(models[key]["items"]).lower()
                for term in terms:
                    self.assertIn(term, description)
