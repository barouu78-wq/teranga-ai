"""Regression tests for Teranga AI's request security helpers."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app


class CsrfTokenTests(unittest.TestCase):
    def test_fresh_token_is_valid(self):
        with patch("app.time.time", return_value=1_000_000):
            token = app.issue_csrf()
            self.assertTrue(app.valid_token(token))

    def test_expired_future_and_tampered_tokens_are_rejected(self):
        with patch("app.time.time", return_value=1_000_000):
            fresh_token = app.issue_csrf()
            future_token = app.sign_token(f"{1_000_061}:nonce")
            expired_token = app.sign_token(
                f"{1_000_000 - app.CSRF_TOKEN_TTL - 1}:nonce"
            )

        with patch("app.time.time", return_value=1_000_000):
            self.assertFalse(app.valid_token(fresh_token + "x"))
            self.assertFalse(app.valid_token(future_token))
            self.assertFalse(app.valid_token(expired_token))


class ChatProtectionTests(unittest.TestCase):
    def test_chat_requires_a_matching_csrf_token(self):
        response = app.app.test_client().post(
            "/chat", json={"message": "Bonjour"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Jeton de sécurité manquant. Recharge la page.")


if __name__ == "__main__":
    unittest.main()
