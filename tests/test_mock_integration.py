"""Integration tests using mocks instead of external FMU files."""

import unittest
from unittest.mock import Mock, patch
import numpy as np

from opentelemetry import trace
from opentelemetry.instrumentation.fmpy import FmpyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class MockModelDescription:
    """Mock model description for testing."""
    def __init__(self, model_name="TestModel", fmi_version="2.0", variables_count=5):
        self.modelName = model_name
        self.fmiVersion = fmi_version
        self.modelVariables = [Mock() for _ in range(variables_count)]


class TestMockIntegration(unittest.TestCase):
    """Integration tests using mocked FMPy operations."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up OpenTelemetry tracing
        self.tracer_provider = TracerProvider()
        self.memory_exporter = InMemorySpanExporter()
        self.span_processor = SimpleSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(self.span_processor)

        # Store the current tracer provider to restore later
        self.previous_tracer_provider = trace.get_tracer_provider()
        trace.set_tracer_provider(self.tracer_provider)

        # Set up instrumentor
        self.instrumentor = FmpyInstrumentor()

    def tearDown(self):
        """Clean up after tests."""
        if self.instrumentor.is_instrumented_by_opentelemetry:
            self.instrumentor.uninstrument()
        self.memory_exporter.clear()
        trace.set_tracer_provider(self.previous_tracer_provider)

    def get_finished_spans(self):
        """Get all finished spans from the memory exporter."""
        self.span_processor.force_flush()
        return self.memory_exporter.get_finished_spans()

    @patch('fmpy.read_model_description')
    def test_model_description_tracing_with_mock(self, mock_read_model):
        """Test model description tracing with mocked FMPy."""
        try:
            import fmpy

            # Set up mock
            mock_model = MockModelDescription("BouncingBall", "2.0", 8)
            mock_read_model.return_value = mock_model

            # Enable instrumentation
            self.instrumentor.instrument()

            # Perform operation
            result = fmpy.read_model_description("test.fmu")

            # Verify operation worked
            self.assertEqual(result.modelName, "BouncingBall")
            mock_read_model.assert_called_once_with("test.fmu")

            # Check spans were created
            spans = self.get_finished_spans()
            self.assertEqual(len(spans), 1)

            span = spans[0]
            self.assertEqual(span.name, "fmpy.read_model_description")

            # Check attributes
            attributes = span.attributes
            self.assertEqual(attributes["code.function"], "read_model_description")
            self.assertEqual(attributes["code.namespace"], "fmpy")
            self.assertEqual(attributes["fmu.filename"], "test.fmu")
            self.assertEqual(attributes["fmu.model_name"], "BouncingBall")
            self.assertEqual(attributes["fmu.fmi_version"], "2.0")
            self.assertEqual(attributes["fmu.variables_count"], 8)

        except ImportError:
            self.skipTest("FMPy not available")

    @patch('fmpy.simulate_fmu')
    def test_simulation_tracing_with_mock(self, mock_simulate):
        """Test simulation tracing with mocked FMPy."""
        try:
            import fmpy

            # Set up mock simulation result
            mock_result = np.array([(0.0, 1.0, 0.0), (0.1, 0.9, -0.1), (0.2, 0.8, -0.2)],
                                 dtype=[('time', 'f8'), ('h', 'f8'), ('v', 'f8')])
            mock_simulate.return_value = mock_result

            # Enable instrumentation
            self.instrumentor.instrument()

            # Perform operation
            result = fmpy.simulate_fmu("bouncing_ball.fmu", stop_time=1.0, start_time=0.0)

            # Verify operation worked
            self.assertEqual(len(result), 3)
            mock_simulate.assert_called_once_with("bouncing_ball.fmu", stop_time=1.0, start_time=0.0)

            # Check spans were created
            spans = self.get_finished_spans()
            self.assertEqual(len(spans), 1)

            span = spans[0]
            self.assertEqual(span.name, "fmpy.simulate_fmu")

            # Check attributes
            attributes = span.attributes
            self.assertEqual(attributes["code.function"], "simulate_fmu")
            self.assertEqual(attributes["code.namespace"], "fmpy")
            self.assertEqual(attributes["fmu.filename"], "bouncing_ball.fmu")
            self.assertEqual(attributes["fmu.stop_time"], 1.0)
            self.assertEqual(attributes["fmu.start_time"], 0.0)
            self.assertEqual(attributes["fmu.result_shape"], "(3,)")
            self.assertEqual(attributes["fmu.variables_count"], 3)

        except ImportError:
            self.skipTest("FMPy not available")

    @patch('fmpy.simulate_fmu')
    def test_simulation_error_tracing_with_mock(self, mock_simulate):
        """Test simulation error tracing with mocked FMPy."""
        try:
            import fmpy

            # Set up mock to raise an error
            mock_simulate.side_effect = RuntimeError("FMU simulation failed")

            # Enable instrumentation
            self.instrumentor.instrument()

            # Perform operation that should fail
            with self.assertRaises(RuntimeError):
                fmpy.simulate_fmu("error.fmu", stop_time=1.0)

            # Check spans were created
            spans = self.get_finished_spans()
            self.assertEqual(len(spans), 1)

            span = spans[0]
            self.assertEqual(span.name, "fmpy.simulate_fmu")

            # Check that error was recorded
            self.assertEqual(span.status.status_code, trace.StatusCode.ERROR)
            self.assertIn("FMU simulation failed", span.status.description)

        except ImportError:
            self.skipTest("FMPy not available")

    @patch('fmpy.read_model_description')
    def test_multiple_operations_with_mock(self, mock_read_model):
        """Test multiple operations create separate spans."""
        try:
            import fmpy

            # Set up mocks for different models
            mock_models = [
                MockModelDescription("Model1", "2.0", 5),
                MockModelDescription("Model2", "3.0", 7),
            ]
            mock_read_model.side_effect = mock_models

            # Enable instrumentation
            self.instrumentor.instrument()

            # Perform multiple operations
            fmpy.read_model_description("model1.fmu")
            fmpy.read_model_description("model2.fmu")

            # Check multiple spans were created
            spans = self.get_finished_spans()
            self.assertEqual(len(spans), 2)

            # Verify span details
            self.assertEqual(spans[0].name, "fmpy.read_model_description")
            self.assertEqual(spans[1].name, "fmpy.read_model_description")

            # Check different models were traced
            self.assertEqual(spans[0].attributes["fmu.model_name"], "Model1")
            self.assertEqual(spans[1].attributes["fmu.model_name"], "Model2")
            self.assertEqual(spans[0].attributes["fmu.fmi_version"], "2.0")
            self.assertEqual(spans[1].attributes["fmu.fmi_version"], "3.0")

        except ImportError:
            self.skipTest("FMPy not available")

    def test_performance_with_mock_operations(self):
        """Test that instrumentation doesn't significantly impact performance."""
        try:
            import fmpy
            import time

            # Mock a fast operation
            mock_model = MockModelDescription("FastModel", "2.0", 3)

            with patch('fmpy.read_model_description', return_value=mock_model):
                # Measure without instrumentation
                start_time = time.time()
                for _ in range(10):
                    fmpy.read_model_description("test.fmu")
                uninstrumented_time = time.time() - start_time

                # Measure with instrumentation
                self.instrumentor.instrument()
                start_time = time.time()
                for _ in range(10):
                    fmpy.read_model_description("test.fmu")
                instrumented_time = time.time() - start_time

                # Instrumentation should not add more than 100% overhead for such simple operations
                self.assertLess(instrumented_time, uninstrumented_time * 2.0)

                # Verify spans were created
                spans = self.get_finished_spans()
                self.assertEqual(len(spans), 10)

        except ImportError:
            self.skipTest("FMPy not available")


if __name__ == "__main__":
    unittest.main()