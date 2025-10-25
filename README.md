# OpenTelemetry FMPy Instrumentation

[![pypi](https://img.shields.io/pypi/v/opentelemetry-instrumentation-fmpy.svg)](https://pypi.org/project/opentelemetry-instrumentation-fmpy/)
[![python](https://img.shields.io/pypi/pyversions/opentelemetry-instrumentation-fmpy.svg)](https://pypi.org/project/opentelemetry-instrumentation-fmpy/)

OpenTelemetry instrumentation for [FMPy](https://github.com/CATIA-Systems/FMPy), providing distributed tracing and observability for Functional Mock-up Unit (FMU) simulations.

## Installation

```bash
pip install opentelemetry-instrumentation-fmpy
```

## Usage

### Programmatic Instrumentation

```python
from opentelemetry.instrumentation.fmpy import FmpyInstrumentor

# Enable instrumentation
FmpyInstrumentor().instrument()

import fmpy
# FMU operations are now traced automatically
result = fmpy.simulate_fmu("model.fmu", stop_time=10.0)

# Disable instrumentation
FmpyInstrumentor().uninstrument()
```


## Configuration

Environment variables:

- `OTEL_PYTHON_FMPY_EXCLUDED_OPERATIONS`: Comma-separated list of FMPy operations to exclude from tracing

## Development

### Requirements

- Python 3.8+
- uv (for development)

## Example

You can run the demo code showing how it is used.

```bash
uv run python demo/main.py <paht-to-fmu-file>
```

## Citation

If you use this repository in your research or publications, please cite it using the following BibTeX entry:

```bibtex
@misc{opentelemetry-instrumentation-fmpy,
  author       = {Christoffer Björkskog},
  title        = {OpenTelemetry Instrumentation for FMPy},
  year         = {2025},
  howpublished = {\url{https://github.com/Novia-RDI-Seafaring/opentelemetry-instrumentation-fmpy}},
  note         = {Contact: christoffer.bjorkskog@novia.fi},
  institution  = {Novia University of Applied Sciences}
}
```



## License

This project is licensed under the MIT - see the [LICENSE](LICENSE) file for details.
