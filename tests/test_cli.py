"""Tests for FMPy instrumentation CLI."""

import io
import sys
import unittest
from unittest.mock import Mock, patch

from opentelemetry.instrumentation.fmpy.cli import main


class TestCLI(unittest.TestCase):
    """Test CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_instrumentor = Mock()

    def test_main_no_args(self):
        """Test main with no arguments shows help."""
        with patch("sys.argv", ["opentelemetry-instrument-fmpy"]):
            result = main([])
            self.assertEqual(result, 1)

    def test_instrument_command(self):
        """Test instrument command."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.return_value = self.mock_instrumentor
            self.mock_instrumentor.is_instrumented_by_opentelemetry = False

            result = main(["instrument"])
            self.assertEqual(result, 0)
            self.mock_instrumentor.instrument.assert_called_once()

    def test_instrument_command_already_instrumented(self):
        """Test instrument command when already instrumented."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.return_value = self.mock_instrumentor
            self.mock_instrumentor.is_instrumented_by_opentelemetry = True

            result = main(["instrument"])
            self.assertEqual(result, 0)
            self.mock_instrumentor.instrument.assert_not_called()

    def test_uninstrument_command(self):
        """Test uninstrument command."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.return_value = self.mock_instrumentor
            self.mock_instrumentor.is_instrumented_by_opentelemetry = True

            result = main(["uninstrument"])
            self.assertEqual(result, 0)
            self.mock_instrumentor.uninstrument.assert_called_once()

    def test_uninstrument_command_not_instrumented(self):
        """Test uninstrument command when not instrumented."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.return_value = self.mock_instrumentor
            self.mock_instrumentor.is_instrumented_by_opentelemetry = False

            result = main(["uninstrument"])
            self.assertEqual(result, 0)
            self.mock_instrumentor.uninstrument.assert_not_called()

    def test_status_command_instrumented(self):
        """Test status command when instrumented."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.return_value = self.mock_instrumentor
            self.mock_instrumentor.is_instrumented_by_opentelemetry = True

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                result = main(["status"])
                self.assertEqual(result, 0)
                self.assertIn("enabled", mock_stdout.getvalue())

    def test_status_command_not_instrumented(self):
        """Test status command when not instrumented."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.return_value = self.mock_instrumentor
            self.mock_instrumentor.is_instrumented_by_opentelemetry = False

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                result = main(["status"])
                self.assertEqual(result, 0)
                self.assertIn("disabled", mock_stdout.getvalue())

    def test_instrument_command_error(self):
        """Test instrument command with error."""
        with patch("opentelemetry.instrumentation.fmpy.cli.FmpyInstrumentor") as mock_class:
            mock_class.side_effect = Exception("Test error")

            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                result = main(["instrument"])
                self.assertEqual(result, 1)
                self.assertIn("Test error", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()