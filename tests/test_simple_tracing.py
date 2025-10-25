"""Simple tracing test to verify instrumentation works."""

import unittest
from pathlib import Path

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.instrumentation.fmpy import FmpyInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class TestBasicTracing(unittest.TestCase):
    """Basic tracing functionality test."""

    @unittest.skipUnless(OTEL_AVAILABLE, "OpenTelemetry not available")
    def test_manual_tracing_verification(self):
        """Manual test to verify tracing works end-to-end."""
        # Set up tracing (only once globally)
        tracer_provider = TracerProvider()
        memory_exporter = InMemorySpanExporter()
        span_processor = SimpleSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)

        # Instrument
        instrumentor = FmpyInstrumentor()
        self.assertFalse(instrumentor.is_instrumented_by_opentelemetry)

        instrumentor.instrument()
        self.assertTrue(instrumentor.is_instrumented_by_opentelemetry)

        try:
            import fmpy

            # Find test FMU
            project_root = Path(__file__).parent.parent
            fmu_search_paths = [
                project_root.parent / "2.0",
                project_root.parent / "3.0",
            ]

            test_fmu = None
            for search_path in fmu_search_paths:
                if search_path.exists():
                    fmu_files = list(search_path.glob("*.fmu"))
                    if fmu_files:
                        test_fmu = fmu_files[0]
                        break

            if test_fmu and test_fmu.exists():
                # Perform operation
                model_description = fmpy.read_model_description(str(test_fmu))

                # Verify operation worked
                self.assertIsNotNone(model_description)
                self.assertIsNotNone(model_description.modelName)

                # Force flush and check spans
                span_processor.force_flush()
                spans = memory_exporter.get_finished_spans()

                # Verify span was created
                self.assertGreater(len(spans), 0, "No spans were created")

                span = spans[0]
                self.assertEqual(span.name, "fmpy.read_model_description")
                self.assertIn("fmu.filename", span.attributes)
                self.assertIn("fmu.model_name", span.attributes)

                print(f"✓ Tracing test passed! Created {len(spans)} span(s)")
                print(f"  Span name: {span.name}")
                print(f"  Model name: {span.attributes.get('fmu.model_name', 'unknown')}")
            else:
                self.skipTest("No FMU files available for testing")

        except ImportError:
            self.skipTest("FMPy not available")

        finally:
            # Clean up
            instrumentor.uninstrument()
            self.assertFalse(instrumentor.is_instrumented_by_opentelemetry)

    def test_cli_functionality(self):
        """Test CLI commands work without errors."""
        from opentelemetry.instrumentation.fmpy.cli import main

        # Test status command
        result = main(["status"])
        self.assertEqual(result, 0)

        # Test instrument command
        result = main(["instrument"])
        self.assertEqual(result, 0)

        # Test status again (should show enabled)
        result = main(["status"])
        self.assertEqual(result, 0)

        # Test uninstrument command
        result = main(["uninstrument"])
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)