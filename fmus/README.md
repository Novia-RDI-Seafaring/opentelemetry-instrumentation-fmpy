# Test FMU Files

This directory contains FMU files for testing the OpenTelemetry instrumentation.

## Directory Structure

```
fmus/
├── README.md                    # This file
├── aarch64-darwin/             # Apple Silicon (ARM64) FMUs
│   ├── BouncingBall.fmu
│   ├── VanDerPol.fmu
│   └── ...
├── x86_64-darwin/              # Intel macOS FMUs
│   ├── BouncingBall.fmu
│   └── ...
├── x86_64-linux/               # Linux x64 FMUs
│   ├── BouncingBall.fmu
│   └── ...
├── x86_64-windows/             # Windows x64 FMUs
│   ├── BouncingBall.fmu
│   └── ...
└── any/                        # Architecture-independent FMUs (if any)
    └── BouncingBall.fmu
```

## Alternative Naming Convention

For single files that need to work across architectures:
```
fmus/
├── BouncingBall.aarch64-darwin.fmu
├── BouncingBall.x86_64-linux.fmu
├── VanDerPol.aarch64-darwin.fmu
└── ...
```

## Git Tracking Rules

**Tracked** (committed to git):
- `fmus/README.md` - This documentation
- `fmus/{arch}/README.md` - Architecture-specific docs
- `fmus/{arch}/*.fmu` - Architecture-specific FMUs
- `fmus/*.{arch}.fmu` - Named architecture FMUs

**Not Tracked** (ignored by git):
- `fmus/*.fmu` - Generic FMU files without architecture suffix
- `fmus/temp/` - Temporary build artifacts
- `fmus/downloads/` - Downloaded FMUs

## Building Test FMUs

To build FMUs for your platform:

```bash
# Build Reference-FMUs for current platform
cd ../Reference-FMUs
mkdir -p build_for_tests && cd build_for_tests
cmake -DFMI_VERSION=3 -DFMI_ARCHITECTURE=$(uname -m) -DWITH_FMUSIM=OFF ..
make -j4

# Copy to our test directory
cp fmus/*.fmu /path/to/opentelemetry-instrumentation-fmpy/fmus/$(uname -m)-$(uname -s | tr '[:upper:]' '[:lower:]')/
```

## Using Test FMUs

The test suite will automatically find FMUs in this directory:

```python
# Tests will look for FMUs in:
# 1. fmus/{current_arch}/
# 2. fmus/any/
# 3. Environment variable FMU_TEST_PATH
# 4. Project test_data/fmus/
```

## FMU Sources

- **Reference-FMUs**: https://github.com/modelica/Reference-FMUs
- **Test-FMUs**: https://github.com/CATIA-Systems/Test-FMUs
- **FMU SDK Examples**: Various online sources

## Architecture Detection

The test suite detects architecture using:
```python
import platform
arch = platform.machine()  # 'arm64', 'x86_64', etc.
system = platform.system().lower()  # 'darwin', 'linux', 'windows'
platform_name = f"{arch}-{system}"
```