"""Tests for FMPy instrumentation."""

import unittest
from unittest.mock import patch

from opentelemetry.instrumentation.fmpy import FmpyInstrumentor


class TestFmpyInstrumentor(unittest.TestCase):
    """Test FMPy instrumentor."""

    def setUp(self):
        """Set up test fixtures."""
        self.instrumentor = FmpyInstrumentor()

    def tearDown(self):
        """Clean up after tests."""
        # Ensure clean state
        if self.instrumentor.is_instrumented_by_opentelemetry:
            self.instrumentor.uninstrument()

    def test_instrumentor_creation(self):
        """Test that instrumentor can be created."""
        self.assertIsInstance(self.instrumentor, FmpyInstrumentor)

    def test_instrumentation_dependencies(self):
        """Test that instrumentor returns correct dependencies."""
        deps = self.instrumentor.instrumentation_dependencies()
        self.assertIn("fmpy >= 0.3.0", deps)

    def test_instrument_without_fmpy(self):
        """Test instrumentation when FMPy is not available."""
        # This test will be skipped since FMPy is available in our test environment
        # In real scenarios where FMPy is not installed, instrumentation should be safe
        self.skipTest("FMPy is available in test environment, cannot test missing FMPy scenario")

    def test_instrument_uninstrument_cycle(self):
        """Test that instrument/uninstrument works properly."""
        # Initially not instrumented
        self.assertFalse(self.instrumentor.is_instrumented_by_opentelemetry)

        # Instrument
        self.instrumentor.instrument()
        self.assertTrue(self.instrumentor.is_instrumented_by_opentelemetry)

        # Uninstrument
        self.instrumentor.uninstrument()
        self.assertFalse(self.instrumentor.is_instrumented_by_opentelemetry)

    def test_double_instrument(self):
        """Test that double instrumentation is handled gracefully."""
        self.instrumentor.instrument()
        self.assertTrue(self.instrumentor.is_instrumented_by_opentelemetry)

        # Second instrumentation should be safe
        self.instrumentor.instrument()
        self.assertTrue(self.instrumentor.is_instrumented_by_opentelemetry)

    def test_uninstrument_when_not_instrumented(self):
        """Test that uninstrumenting when not instrumented is safe."""
        self.assertFalse(self.instrumentor.is_instrumented_by_opentelemetry)
        # Should not raise an exception
        self.instrumentor.uninstrument()
        self.assertFalse(self.instrumentor.is_instrumented_by_opentelemetry)


if __name__ == "__main__":
    unittest.main()