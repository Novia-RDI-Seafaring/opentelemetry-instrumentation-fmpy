"""Standalone demonstration of FMPy instrumentation functionality."""

import unittest
from unittest.mock import Mock, patch
import numpy as np

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.instrumentation.fmpy import FmpyInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class MockModelDescription:
    """Mock model description for testing."""
    def __init__(self, model_name="TestModel", fmi_version="2.0", variables_count=5):
        self.modelName = model_name
        self.fmiVersion = fmi_version
        self.modelVariables = [Mock() for _ in range(variables_count)]


class TestStandaloneDemo(unittest.TestCase):
    """Standalone demonstration tests."""

    @unittest.skipUnless(OTEL_AVAILABLE, "OpenTelemetry not available")
    def test_complete_instrumentation_workflow(self):
        """Complete end-to-end test of instrumentation workflow."""
        print("\n" + "="*60)
        print("🧪 STANDALONE FMPy INSTRUMENTATION DEMO")
        print("="*60)

        # Set up tracing (global setup - only done once)
        tracer_provider = TracerProvider()
        memory_exporter = InMemorySpanExporter()
        span_processor = SimpleSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)

        # Create instrumentor
        instrumentor = FmpyInstrumentor()
        print("✓ Created FmpyInstrumentor")

        # Test 1: Basic instrumentation
        print("\n📋 Test 1: Basic Instrumentation")
        self.assertFalse(instrumentor.is_instrumented_by_opentelemetry)
        print("  ✓ Initially not instrumented")

        instrumentor.instrument()
        self.assertTrue(instrumentor.is_instrumented_by_opentelemetry)
        print("  ✓ Successfully instrumented")

        try:
            import fmpy
            print("  ✓ FMPy imported successfully")

            # Test 2: Mock model description tracing
            print("\n📋 Test 2: Model Description Tracing")
            mock_model = MockModelDescription("TestBouncingBall", "2.0", 8)

            with patch.object(instrumentor, '_original_read_model_description', return_value=mock_model):
                result = fmpy.read_model_description("test_bouncing_ball.fmu")
                print(f"  ✓ Model name: {result.modelName}")
                print(f"  ✓ FMI version: {result.fmiVersion}")
                print(f"  ✓ Variables count: {len(result.modelVariables)}")

            # Check span
            span_processor.force_flush()
            spans = memory_exporter.get_finished_spans()
            self.assertGreater(len(spans), 0, "No spans were created for model description")

            model_span = spans[-1]
            self.assertEqual(model_span.name, "fmpy.read_model_description")
            print(f"  ✓ Span created: {model_span.name}")
            print(f"  ✓ Traced model: {model_span.attributes.get('fmu.model_name', 'unknown')}")

            memory_exporter.clear()

            # Test 3: Mock simulation tracing
            print("\n📋 Test 3: Simulation Tracing")
            mock_result = np.array([(0.0, 1.0, 0.0), (0.1, 0.9, -0.1), (0.2, 0.8, -0.2)],
                                 dtype=[('time', 'f8'), ('h', 'f8'), ('v', 'f8')])

            with patch.object(instrumentor, '_original_simulate_fmu', return_value=mock_result):
                result = fmpy.simulate_fmu("test_simulation.fmu", stop_time=1.0, start_time=0.0)
                print(f"  ✓ Simulation completed, shape: {result.shape}")
                print(f"  ✓ Variables: {list(result.dtype.names)}")

            # Check simulation span
            span_processor.force_flush()
            sim_spans = memory_exporter.get_finished_spans()
            self.assertGreater(len(sim_spans), 0, "No spans were created for simulation")

            sim_span = sim_spans[-1]
            self.assertEqual(sim_span.name, "fmpy.simulate_fmu")
            print(f"  ✓ Span created: {sim_span.name}")
            print(f"  ✓ Stop time: {sim_span.attributes.get('fmu.stop_time', 'unknown')}")
            print(f"  ✓ Result shape: {sim_span.attributes.get('fmu.result_shape', 'unknown')}")

            memory_exporter.clear()

            # Test 4: Error handling
            print("\n📋 Test 4: Error Handling")
            with patch.object(instrumentor, '_original_simulate_fmu', side_effect=RuntimeError("Test error")):
                try:
                    fmpy.simulate_fmu("error_test.fmu", stop_time=1.0)
                    self.fail("Expected RuntimeError was not raised")
                except RuntimeError as e:
                    print(f"  ✓ Exception caught: {e}")

            # Check error span
            span_processor.force_flush()
            error_spans = memory_exporter.get_finished_spans()
            self.assertGreater(len(error_spans), 0, "No spans were created for error case")

            error_span = error_spans[-1]
            self.assertEqual(error_span.name, "fmpy.simulate_fmu")
            self.assertEqual(error_span.status.status_code, trace.StatusCode.ERROR)
            print(f"  ✓ Error span created: {error_span.name}")
            print(f"  ✓ Error status: {error_span.status.status_code.name}")

        except ImportError:
            print("  ⚠️  FMPy not available - skipping FMPy tests")

        # Test 5: Uninstrumentation
        print("\n📋 Test 5: Uninstrumentation")
        instrumentor.uninstrument()
        self.assertFalse(instrumentor.is_instrumented_by_opentelemetry)
        print("  ✓ Successfully uninstrumented")

        # Summary
        span_processor.force_flush()
        total_spans = memory_exporter.get_finished_spans()
        print(f"\n📊 SUMMARY:")
        print(f"  Total spans created: {len(total_spans)}")
        for i, span in enumerate(total_spans):
            status_icon = "✅" if span.status.status_code.name == "UNSET" else "❌"
            print(f"  {status_icon} Span {i+1}: {span.name} ({span.status.status_code.name})")

        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)

    def test_cli_integration(self):
        """Test CLI integration works."""
        from opentelemetry.instrumentation.fmpy.cli import main

        print("\n🔧 Testing CLI functionality...")

        # Test all CLI commands
        commands_to_test = [
            (["status"], "status check"),
            (["instrument"], "instrumentation"),
            (["status"], "status after instrument"),
            (["uninstrument"], "uninstrumentation"),
            (["status"], "final status check"),
        ]

        for cmd, description in commands_to_test:
            result = main(cmd)
            self.assertEqual(result, 0, f"CLI {description} failed")
            print(f"  ✓ CLI {description} passed")

        print("  ✓ All CLI tests passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)