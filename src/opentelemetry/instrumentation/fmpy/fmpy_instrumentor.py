"""FMPy instrumentation for OpenTelemetry."""

import logging
from typing import Collection

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.fmpy.package import _instruments
from opentelemetry.instrumentation.fmpy.version import __version__

logger = logging.getLogger(__name__)


class FmpyInstrumentor(BaseInstrumentor):
    """An instrumentor for FMPy.

    This instrumentor provides OpenTelemetry tracing for FMPy FMU operations.
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return a list of python packages with versions that the instrumentation supports.

        Returns:
            The list of supported packages.
        """
        return _instruments

    def _instrument(self, **kwargs):
        """Instruments FMPy.

        Args:
            **kwargs: Optional arguments specific to this instrumentation.
        """
        logger.debug("Instrumenting FMPy")

        # Import here to avoid issues if fmpy is not installed
        try:
            import fmpy
        except ImportError:
            logger.warning("FMPy not found, skipping instrumentation")
            return

        from opentelemetry.instrumentation.utils import unwrap
        from opentelemetry.trace import get_tracer
        from opentelemetry import trace, metrics
        from opentelemetry.semconv.trace import SpanAttributes

        tracer = get_tracer(__name__, __version__)
        meter = metrics.get_meter(__name__, __version__)

        # Store original functions for unwrapping
        self._original_simulate_fmu = getattr(fmpy, 'simulate_fmu', None)
        self._original_read_model_description = getattr(fmpy, 'read_model_description', None)

        # Cache for model descriptions to avoid re-reading during simulation
        self._model_cache = {}

        # Create metrics for simulation data
        self._simulation_counter = meter.create_counter(
            name="fmu.simulations.total",
            description="Total number of FMU simulations performed"
        )
        self._simulation_duration = meter.create_histogram(
            name="fmu.simulation.duration_seconds",
            description="Duration of FMU simulations in seconds"
        )
        self._variable_value_gauge = meter.create_gauge(
            name="fmu.variable.value",
            description="Current value of FMU variables during simulation"
        )

        # Instrument simulate_fmu
        if self._original_simulate_fmu:
            def _instrumented_simulate_fmu(filename, *args, **kwargs):
                with tracer.start_as_current_span(
                    "fmpy.simulate_fmu",
                    attributes={
                        SpanAttributes.CODE_FUNCTION: "simulate_fmu",
                        SpanAttributes.CODE_NAMESPACE: "fmpy",
                        "fmu.filename": str(filename) if filename else "unknown",
                        "fmu.stop_time": kwargs.get('stop_time', 'unknown'),
                        "fmu.start_time": kwargs.get('start_time', 0.0),
                        "fmu.fmi_type": kwargs.get('fmi_type', 'auto'),
                    }
                ) as span:
                    try:
                        result = self._original_simulate_fmu(filename, *args, **kwargs)

                        # Record the FMI type that was used
                        fmi_type_used = kwargs.get('fmi_type', 'default')
                        span.set_attribute("fmu.fmi_type_used", fmi_type_used)

                        # Basic result information
                        if hasattr(result, 'shape'):
                            span.set_attribute("fmu.result_shape", str(result.shape))
                            span.set_attribute("fmu.result_points", int(result.shape[0]))

                        if hasattr(result, 'dtype') and hasattr(result.dtype, 'names'):
                            variable_names = list(result.dtype.names)
                            span.set_attribute("fmu.variables_count", len(variable_names))
                            span.set_attribute("fmu.variable_names", str(variable_names[:10]))  # Limit to first 10

                            # Get model description to understand variable causality
                            model_desc = None
                            filename_str = str(filename) if filename else ""
                            if filename_str in self._model_cache:
                                model_desc = self._model_cache[filename_str]
                            else:
                                try:
                                    model_desc = self._original_read_model_description(filename)
                                    self._model_cache[filename_str] = model_desc
                                except:
                                    pass

                            # Build causality mapping
                            var_causality = {}
                            if model_desc and hasattr(model_desc, 'modelVariables'):
                                for var in model_desc.modelVariables:
                                    var_causality[var.name] = getattr(var, 'causality', 'unknown')

                            # Capture simulation states - organized by causality
                            input_states = {}
                            output_states = {}

                            for var_name in variable_names[:10]:  # Limit to first 10 variables
                                try:
                                    var_data = result[var_name]
                                    if len(var_data) > 0:
                                        # Build variable state info
                                        var_states = {
                                            "initial": float(var_data[0]),
                                            "final": float(var_data[-1])
                                        }

                                        # Add min/max for non-time variables
                                        if var_name != 'time' and len(var_data) > 1:
                                            var_states["min"] = float(min(var_data))
                                            var_states["max"] = float(max(var_data))

                                        # Categorize by causality
                                        causality = var_causality.get(var_name, 'unknown')
                                        if causality == 'input':
                                            input_states[var_name] = var_states
                                        elif causality in ('output', 'independent'):
                                            output_states[var_name] = var_states

                                        if var_name == 'time':
                                            span.set_attribute("fmu.final_time", float(var_data[-1]))
                                except (IndexError, ValueError, TypeError):
                                    continue

                            # Add separate events for inputs and outputs with nested structure
                            if input_states:
                                for var_name, var_states in input_states.items():
                                    span.add_event(f"simulation.input.{var_name}", var_states)

                            if output_states:
                                # Only show outputs that changed or have interesting values
                                interesting_outputs = {}
                                for var_name, var_states in output_states.items():
                                    # Skip time variable and zero-only outputs
                                    if var_name == 'time':
                                        continue

                                    initial = var_states.get('initial', 0)
                                    final = var_states.get('final', 0)
                                    min_val = var_states.get('min', 0)
                                    max_val = var_states.get('max', 0)

                                    # Include if: values changed, or non-zero values, or has variation
                                    if (initial != final or
                                        abs(initial) > 1e-10 or abs(final) > 1e-10 or
                                        min_val != max_val):
                                        interesting_outputs[var_name] = var_states

                                # Add summary if we filtered out variables
                                if len(interesting_outputs) < len(output_states) - 1:  # -1 for time
                                    filtered_count = len(output_states) - len(interesting_outputs) - 1
                                    span.add_event("simulation.summary", {
                                        "active_outputs": len(interesting_outputs),
                                        "filtered_zero_outputs": filtered_count,
                                        "total_outputs": len(output_states) - 1
                                    })

                                # Add the interesting outputs
                                for var_name, var_states in interesting_outputs.items():
                                    span.add_event(f"simulation.output.{var_name}", var_states)

                                # Always include time as a summary
                                if 'time' in output_states:
                                    time_data = output_states['time']
                                    span.add_event("simulation.timing", {
                                        "duration": time_data.get('final', 0) - time_data.get('initial', 0),
                                        "start": time_data.get('initial', 0),
                                        "end": time_data.get('final', 0)
                                    })

                            # Add simulation statistics
                            try:
                                time_var = result['time'] if 'time' in variable_names else result[variable_names[0]]
                                if len(time_var) > 1:
                                    time_step = float(time_var[1] - time_var[0])
                                    span.set_attribute("fmu.time_step", time_step)
                            except (KeyError, IndexError, ValueError):
                                pass

                        # Record simulation metrics
                        self._record_simulation_metrics(filename, result, kwargs, span)

                        return result
                    except Exception as e:
                        # Record failed simulation
                        self._simulation_counter.add(1, {
                            "fmu.model": str(filename).split('/')[-1] if filename else "unknown",
                            "status": "error",
                            "error.type": type(e).__name__
                        })
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise

            fmpy.simulate_fmu = _instrumented_simulate_fmu

        # Instrument read_model_description
        if self._original_read_model_description:
            def _instrumented_read_model_description(filename, *args, **kwargs):
                with tracer.start_as_current_span(
                    "fmpy.read_model_description",
                    attributes={
                        SpanAttributes.CODE_FUNCTION: "read_model_description",
                        SpanAttributes.CODE_NAMESPACE: "fmpy",
                        "fmu.filename": str(filename) if filename else "unknown",
                    }
                ) as span:
                    try:
                        result = self._original_read_model_description(filename, *args, **kwargs)
                        if result:
                            span.set_attribute("fmu.model_name", getattr(result, 'modelName', 'unknown'))
                            span.set_attribute("fmu.fmi_version", getattr(result, 'fmiVersion', 'unknown'))
                            span.set_attribute("fmu.guid", getattr(result, 'guid', 'unknown'))
                            span.set_attribute("fmu.generation_tool", getattr(result, 'generationTool', 'unknown'))
                            span.set_attribute("fmu.description", getattr(result, 'description', 'unknown'))
                            span.set_attribute("fmu.variable_naming_convention", getattr(result, 'variableNamingConvention', 'unknown'))

                            if hasattr(result, 'modelVariables'):
                                variables = result.modelVariables
                                span.set_attribute("fmu.variables_count", len(variables))

                                # Detailed variable information
                                var_details = []
                                for var in variables[:5]:  # Limit to first 5 for readability
                                    var_info = {
                                        'name': getattr(var, 'name', 'unknown'),
                                        'type': getattr(var, 'type', 'unknown'),
                                        'causality': getattr(var, 'causality', 'unknown'),
                                        'variability': getattr(var, 'variability', 'unknown'),
                                        'description': getattr(var, 'description', None),
                                        'start': getattr(var, 'start', None),
                                        'min': getattr(var, 'min', None),
                                        'max': getattr(var, 'max', None),
                                        'unit': getattr(var, 'unit', None),
                                    }
                                    # Clean up None values for cleaner telemetry
                                    var_info = {k: v for k, v in var_info.items() if v is not None}
                                    var_details.append(var_info)

                                # Add variable details as span events for better structure
                                for i, var_info in enumerate(var_details):
                                    event_name = f"model.variable.{var_info['name']}"
                                    span.add_event(event_name, var_info)

                            if hasattr(result, 'defaultExperiment'):
                                exp = result.defaultExperiment
                                if exp:
                                    start_time = getattr(exp, 'startTime', None)
                                    stop_time = getattr(exp, 'stopTime', None)
                                    step_size = getattr(exp, 'stepSize', None)

                                    if start_time is not None:
                                        span.set_attribute("fmu.default_start_time", start_time)
                                    if stop_time is not None:
                                        span.set_attribute("fmu.default_stop_time", stop_time)
                                    if step_size is not None:
                                        span.set_attribute("fmu.default_step_size", step_size)

                            span.set_attribute("fmu.continuous_states_count", getattr(result, 'numberOfContinuousStates', 0))
                            span.set_attribute("fmu.event_indicators_count", getattr(result, 'numberOfEventIndicators', 0))

                            # Interface support
                            interfaces = []
                            if hasattr(result, 'modelExchange') and result.modelExchange:
                                interfaces.append('ModelExchange')
                            if hasattr(result, 'coSimulation') and result.coSimulation:
                                interfaces.append('CoSimulation')
                            if hasattr(result, 'scheduledExecution') and result.scheduledExecution:
                                interfaces.append('ScheduledExecution')
                            span.set_attribute("fmu.supported_interfaces", str(interfaces))

                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise

            fmpy.read_model_description = _instrumented_read_model_description

    def _record_simulation_metrics(self, filename, result, kwargs, span):
        """Record metrics for simulation data that can be graphed."""
        try:
            # Extract model name for labeling
            model_name = str(filename).split('/')[-1] if filename else "unknown"

            # Record successful simulation
            self._simulation_counter.add(1, {
                "fmu.model": model_name,
                "status": "success",
                "fmi.type": kwargs.get('fmi_type', 'default')
            })

            # Record simulation duration
            start_time = kwargs.get('start_time', 0.0)
            stop_time = kwargs.get('stop_time', 1.0)
            duration = float(stop_time) - float(start_time)
            self._simulation_duration.record(duration, {
                "fmu.model": model_name
            })

            # Record variable values as time series data
            if hasattr(result, 'dtype') and hasattr(result.dtype, 'names'):
                variable_names = list(result.dtype.names)

                # Get time points for timestamping
                time_data = result.get('time', None) if 'time' in variable_names else None

                # Record each variable's data points for graphing
                for var_name in variable_names[:5]:  # Limit to first 5 variables
                    if var_name == 'time':
                        continue  # Skip time variable itself

                    try:
                        var_data = result[var_name]
                        if len(var_data) > 0:
                            # Record multiple data points for time series
                            for i, value in enumerate(var_data):
                                # Use actual time if available, otherwise use index
                                timestamp_attrs = {
                                    "fmu.model": model_name,
                                    "fmu.variable": var_name,
                                    "simulation.time": float(time_data[i]) if time_data is not None and i < len(time_data) else float(i)
                                }

                                self._variable_value_gauge.set(float(value), timestamp_attrs)

                    except (IndexError, ValueError, TypeError, KeyError):
                        continue

        except Exception:
            # Don't let metrics recording break the simulation
            pass

    def _uninstrument(self, **kwargs):
        """Uninstruments FMPy.

        Args:
            **kwargs: Optional arguments specific to this instrumentation.
        """
        logger.debug("Uninstrumenting FMPy")

        try:
            import fmpy
        except ImportError:
            logger.warning("FMPy not found, skipping uninstrumentation")
            return

        # Restore original functions
        if hasattr(self, '_original_simulate_fmu') and self._original_simulate_fmu:
            fmpy.simulate_fmu = self._original_simulate_fmu

        if hasattr(self, '_original_read_model_description') and self._original_read_model_description:
            fmpy.read_model_description = self._original_read_model_description