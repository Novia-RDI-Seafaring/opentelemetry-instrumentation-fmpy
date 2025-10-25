"""Integration tests for FMPy instrumentation with actual FMUs."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.instrumentation.fmpy import FmpyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class TestFmpyIntegration(unittest.TestCase):
    """Integration tests with actual FMU files."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the class."""
        # Look for FMU files in common locations but don't require them
        cls.test_fmus = cls._find_available_fmus()

    @classmethod
    def _find_available_fmus(cls):
        """Find available FMU files for testing, if any."""
        import platform

        possible_paths = []
        project_root = Path(__file__).parent.parent

        # Detect current platform
        arch = platform.machine()
        if arch == 'arm64':
            arch = 'aarch64'  # Normalize ARM64 naming
        system = platform.system().lower()
        platform_name = f"{arch}-{system}"

        # Check architecture-specific FMUs first (highest priority)
        arch_fmu_path = project_root / "fmus" / platform_name
        if arch_fmu_path.exists():
            possible_paths.append(arch_fmu_path)

        # Check generic FMUs directory
        generic_fmu_path = project_root / "fmus" / "any"
        if generic_fmu_path.exists():
            possible_paths.append(generic_fmu_path)

        # Check if there's an FMU_TEST_PATH environment variable
        fmu_test_path = os.environ.get('FMU_TEST_PATH')
        if fmu_test_path:
            test_path = Path(fmu_test_path)
            if test_path.exists():
                possible_paths.append(test_path)

        # Check legacy test data locations
        legacy_locations = [
            project_root / "test_data" / "fmus",
            project_root / "fmus",  # Root fmus directory
        ]

        for location in legacy_locations:
            if location.exists() and location not in possible_paths:
                possible_paths.append(location)

        # Collect FMU files
        test_fmus = []
        for search_path in possible_paths:
            if search_path.is_dir():
                fmu_files = list(search_path.glob("*.fmu"))
                test_fmus.extend(fmu_files)
            elif search_path.suffix == '.fmu':
                test_fmus.append(search_path)

        return test_fmus[:5]  # Limit to 5 FMUs for testing

    def setUp(self):
        """Set up test fixtures."""
        # Set up OpenTelemetry tracing
        self.tracer_provider = TracerProvider()
        self.memory_exporter = InMemorySpanExporter()
        self.span_processor = SimpleSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(self.span_processor)
        trace.set_tracer_provider(self.tracer_provider)

        # Set up instrumentor
        self.instrumentor = FmpyInstrumentor()

    def tearDown(self):
        """Clean up after tests."""
        if self.instrumentor.is_instrumented_by_opentelemetry:
            self.instrumentor.uninstrument()
        self.memory_exporter.clear()

    def test_fmu_model_description_inspection(self):
        """Test FMU model description inspection works."""
        if not self.test_fmus or not Path(self.test_fmus[0]).exists():
            self.skipTest("No FMU files available for testing")

        try:
            import fmpy

            fmu_path = str(self.test_fmus[0])

            # Test model description reading
            model_description = fmpy.read_model_description(fmu_path)

            self.assertIsNotNone(model_description)
            self.assertIsNotNone(model_description.modelName)
            self.assertIsNotNone(model_description.fmiVersion)
            self.assertIsInstance(model_description.modelVariables, list)

        except ImportError:
            self.skipTest("FMPy not available")
        except Exception as e:
            self.fail(f"FMU inspection failed: {e}")

    def test_instrumentation_with_fmu_inspection(self):
        """Test that instrumentation works with FMU inspection."""
        if not self.test_fmus or not Path(self.test_fmus[0]).exists():
            self.skipTest("No FMU files available for testing")

        try:
            import fmpy

            # Enable instrumentation
            self.instrumentor.instrument()

            fmu_path = str(self.test_fmus[0])

            # Perform FMU operation
            model_description = fmpy.read_model_description(fmu_path)

            # Verify basic functionality still works
            self.assertIsNotNone(model_description)

            # For now, just verify instrumentation doesn't break anything
            # TODO: Add actual tracing verification when instrumentation is implemented

        except ImportError:
            self.skipTest("FMPy not available")
        except Exception as e:
            self.fail(f"Instrumented FMU inspection failed: {e}")

    @patch('fmpy.simulate_fmu')
    def test_instrumentation_with_mock_simulation(self, mock_simulate):
        """Test instrumentation with mocked FMU simulation."""
        try:
            import fmpy
            import numpy as np

            # Mock simulation result
            mock_result = np.array([(0.0, 1.0, 0.0), (0.1, 0.9, -0.1)],
                                 dtype=[('time', 'f8'), ('h', 'f8'), ('v', 'f8')])
            mock_simulate.return_value = mock_result

            # Enable instrumentation
            self.instrumentor.instrument()

            # Perform simulated FMU operation
            result = fmpy.simulate_fmu("dummy.fmu", stop_time=1.0)

            # Verify mock was called and result is correct
            mock_simulate.assert_called_once()
            self.assertEqual(len(result), 2)

            # TODO: Add span verification when instrumentation is implemented

        except ImportError:
            self.skipTest("FMPy not available")

    def test_multiple_fmu_operations(self):
        """Test instrumentation with multiple FMU operations."""
        if len(self.test_fmus) < 2:
            self.skipTest("Need at least 2 FMU files for this test")

        try:
            import fmpy

            # Enable instrumentation
            self.instrumentor.instrument()

            results = []
            for fmu_path in self.test_fmus[:2]:  # Test with first 2 FMUs
                if Path(fmu_path).exists():
                    model_description = fmpy.read_model_description(str(fmu_path))
                    results.append(model_description.modelName)

            self.assertGreater(len(results), 0)

            # TODO: Verify multiple spans when instrumentation is implemented

        except ImportError:
            self.skipTest("FMPy not available")
        except Exception as e:
            self.fail(f"Multiple FMU operations failed: {e}")

    def test_fmu_error_handling(self):
        """Test that instrumentation handles FMU errors gracefully."""
        try:
            import fmpy

            # Enable instrumentation
            self.instrumentor.instrument()

            # Try to read a non-existent FMU
            with self.assertRaises(Exception):
                fmpy.read_model_description("non_existent.fmu")

            # Ensure instrumentation doesn't interfere with error handling

        except ImportError:
            self.skipTest("FMPy not available")

    def test_instrumentation_performance_impact(self):
        """Test that instrumentation doesn't significantly impact performance."""
        if not self.test_fmus or not Path(self.test_fmus[0]).exists():
            self.skipTest("No FMU files available for testing")

        try:
            import fmpy
            import time

            fmu_path = str(self.test_fmus[0])

            # Measure without instrumentation
            start_time = time.time()
            for _ in range(5):
                fmpy.read_model_description(fmu_path)
            uninstrumented_time = time.time() - start_time

            # Measure with instrumentation
            self.instrumentor.instrument()
            start_time = time.time()
            for _ in range(5):
                fmpy.read_model_description(fmu_path)
            instrumented_time = time.time() - start_time

            # Instrumentation should not add more than 50% overhead
            self.assertLess(instrumented_time, uninstrumented_time * 1.5)

        except ImportError:
            self.skipTest("FMPy not available")
        except Exception as e:
            self.fail(f"Performance test failed: {e}")


if __name__ == "__main__":
    unittest.main()