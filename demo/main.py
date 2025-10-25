#!/usr/bin/env python3
"""Minimal FMPy + OpenTelemetry demo with RichConsole exporter by default."""

import os
import sys
from pathlib import Path
import fmpy

from opentelemetry import trace
from opentelemetry.instrumentation.fmpy import FmpyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.richconsole import RichConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
import typer
app = typer.Typer(help="Run FMPy simulation with OpenTelemetry tracing.")

@app.command()
def run_simulation(
    fmu_path: Path = typer.Argument(..., help="Path to the FMU file"),
    stop_time: float = typer.Option(1.0, help="Simulation stop time"),
    show_metrics: bool = typer.Option(False, help="Show metrics"),
):
    resource = Resource.create({"service.name": "opentelemetry-instrumentation-fmpy-demo"})
    tracer_provider = make_output_look_nicer(resource)
    
    # this is where the magic happens: we instrument the FMPy library
    FmpyInstrumentor().instrument()

    if show_metrics:
        print("i have not added this yet to this demo... but it is supported...")


    # enve thoug we dont pritnw we will still see the useful information in the console
    model_description = fmpy.read_model_description(fmu_path)
    result = fmpy.simulate_fmu(fmu_path, stop_time=stop_time)



def make_output_look_nicer(resource: Resource) -> TracerProvider:
    tracer_provider = TracerProvider(resource=resource)
    # how we render the spans in the console
    tracer_provider.add_span_processor(SimpleSpanProcessor(RichConsoleSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    return tracer_provider

if __name__ == "__main__":
    

    # this fn that runs teh  will not print anything, but we will still see the useful information in the console
    app()