from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import langfuse

from app import tracing


class TracingAdapterTests(unittest.TestCase):
    def test_adapter_uses_the_installed_langfuse_v3_api(self) -> None:
        self.assertEqual(tracing.observe.__module__, langfuse.observe.__module__)
        client = tracing.get_langfuse_client()
        self.assertTrue(callable(client.update_current_trace))
        self.assertTrue(callable(client.update_current_generation))

    def test_tracing_is_disabled_without_both_keys(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(tracing.tracing_enabled())

        with patch.dict(os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-only"}, clear=True):
            self.assertFalse(tracing.tracing_enabled())

    def test_flush_is_a_no_op_without_keys(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(tracing, "get_langfuse_client") as client_factory:
                tracing.flush_tracing()
                client_factory.assert_not_called()

    def test_flush_never_propagates_telemetry_errors(self) -> None:
        keys = {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}
        with patch.dict(os.environ, keys, clear=True):
            with patch.object(tracing, "get_langfuse_client") as client_factory:
                client_factory.return_value.flush.side_effect = RuntimeError("network down")
                tracing.flush_tracing()  # không được raise
                client_factory.return_value.flush.assert_called_once()


if __name__ == "__main__":
    unittest.main()
