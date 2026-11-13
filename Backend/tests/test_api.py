import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch.dict(os.environ, {"FIREBASE_ENABLED": "false"})
    def test_local_hello_does_not_access_firebase(self):
        with patch("app.main.get_firestore_client") as factory:
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "hello word", "source": "local"})
        factory.assert_not_called()

    @patch.dict(os.environ, {"FIREBASE_ENABLED": "true"})
    @patch("app.main.get_firestore_client")
    def test_firestore_message(self, factory):
        document = MagicMock()
        document.to_dict.return_value = {"text": "hello word from Firebase"}
        collection = factory.return_value.collection.return_value
        collection.document.return_value.get.return_value = document
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "message": "hello word from Firebase", "source": "firestore"
        })
        factory.return_value.collection.assert_called_once_with("messages")
        collection.document.assert_called_once_with("hello")

    @patch.dict(os.environ, {"FIREBASE_ENABLED": "true"})
    @patch("app.main.get_firestore_client")
    def test_missing_or_invalid_firestore_message(self, factory):
        document = factory.return_value.collection.return_value.document.return_value.get.return_value
        for payload in (None, {}, {"text": 123}, {"text": " "}):
            with self.subTest(payload=payload):
                document.to_dict.return_value = payload
                self.assertEqual(self.client.get("/").status_code, 503)

    @patch.dict(os.environ, {"FIREBASE_ENABLED": "true"})
    @patch("app.main.get_firestore_client", side_effect=RuntimeError("credentials missing"))
    def test_firebase_error_and_independent_health(self, factory):
        with self.assertLogs("app.main", level="ERROR"):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Firebase unavailable"})
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
