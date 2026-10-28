import os
import unittest
from unittest.mock import patch

from app.config import Settings


class GeminiSettingsTests(unittest.TestCase):
    def test_gemini_key_environment_alias(self):
        with patch.dict(os.environ, {"GEMINI_KEY": "alias-test-key"}, clear=True):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.gemini_api_key, "alias-test-key")
        self.assertEqual(settings.llm_provider, "gemini")

    def test_canonical_environment_name_takes_precedence(self):
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "canonical-test-key", "GEMINI_KEY": "alias-test-key"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.gemini_api_key, "canonical-test-key")

    def test_python_field_name_remains_supported(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None, gemini_api_key="explicit-test-key")

        self.assertEqual(settings.gemini_api_key, "explicit-test-key")
