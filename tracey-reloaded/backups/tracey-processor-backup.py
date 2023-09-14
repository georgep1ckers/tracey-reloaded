from flask import Flask, jsonify
import logging
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

logging.basicConfig(level=logging.INFO)

# Get the local otel collector IP
OTEL_HOST = os.environ.get("OTEL_HOST", default="10.10.0.12:4317")
if not ":" in OTEL_HOST:
  OTEL_HOST = OTEL_HOST + ":4317"
print("OTEL Collector Address: {}".format(OTEL_HOST))

# Set OTEL service name and set the trace provider
resource = Resource(
    attributes={
        "service.name": "order-processor",
        "version": "v0.0.1",
        "service.instance.id": "instance-1",
    }
)
trace.set_tracer_provider(TracerProvider(resource=resource))


# Create OTLP exporter and point it to the OTEL Collector
# Replace "otel-collector:4317" with the address of your OTEL Collector
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_HOST, insecure=True)

# Set up BatchSpanProcessor and add it to the tracer provider
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

# Instrument Flask app
FlaskInstrumentor().instrument_app(app)

orders = [
    {'order_id': 1, 'product': 'Widget A', 'quantity': 1000},
    {'order_id': 2, 'product': 'Widget B', 'quantity': 500},
    {'order_id': 4, 'product': 'Widget A', 'quantity': 1500},
    {'order_id': 5, 'product': 'Widget B', 'quantity': 250},
    # Add more orders as needed
]

@app.route('/')
def get_order():
    with tracer.start_as_current_span("Get Order"):
        if orders:
            with tracer.start_as_current_span("Retrieve Order"):
                order = orders.pop(0) # Retrieve the next order
                app.logger.info(f'Order {order["order_id"]} was picked')
                return jsonify(order)
        else:
            with tracer.start_as_current_span("No More Orders"):
                return jsonify({'message': 'No more orders'}), 204

if __name__ == "__main__":
    app.logger.info('Processor is starting...')
    app.run(host="0.0.0.0", port=8080)