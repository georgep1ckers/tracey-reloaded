
from flask import Flask, jsonify, request
import logging
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry import context
from opentelemetry.propagate import extract
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.trace import get_current_span

logging.basicConfig(level=logging.INFO)

def custom_logger(message, level='info'):
    current_span = get_current_span()
    if current_span.is_recording():
        trace_id = current_span.get_span_context().trace_id
        span_id = current_span.get_span_context().span_id
        # Convert to hexadecimal format
        trace_id_hex = "{:032x}".format(trace_id)
        span_id_hex = "{:016x}".format(span_id)
    else:
        trace_id_hex = span_id_hex = 'N/A'

    log_message = f"[TraceID: {trace_id_hex}, SpanID: {span_id_hex}] {message}"

    if level == 'info':
        logging.info(log_message)
    elif level == 'error':
        logging.error(log_message)
    elif level == 'warning':
        logging.warning(log_message)
    else:
        logging.debug(log_message)


# Constants
DATABASE_MAX_CONNECTIONS = 10

# Get the local otel collector IP
OTEL_HOST = os.environ.get("OTEL_HOST", default="10.10.0.12:4317")
if not ":" in OTEL_HOST:
    OTEL_HOST = OTEL_HOST + ":4317"
print("OTEL Collector Address: {}".format(OTEL_HOST))

# Set OTEL service name and set the trace provider
resource = Resource(
    attributes={
        "service.name": "stock-controller",
        "version": "v0.0.1",
        "service.instance.id": "instance-1",
        "telemetry.sdk.name":"opentelemetry",
        "telemetry.sdk.language":"python",
        "telemetry.sdk.version":"1.19.0"
    }
)
trace.set_tracer_provider(TracerProvider(resource=resource))

# Create OTLP exporter and point it to the OTEL Collector
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_HOST, insecure=True)

# Set up BatchSpanProcessor and add it to the tracer provider
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

# Instrument Flask app
FlaskInstrumentor().instrument_app(app)

# Database parameters:
db_params = {
    'dbname': "mydatabase",
    'user': "user",
    'password': "password",
    'host': "postgresql",
    'port': 5432,
}

# Instrument psycopg2
Psycopg2Instrumentor().instrument(skip_dep_check=True, enable_commenter=True)

# Set up a database connection pool
pool = SimpleConnectionPool(
    minconn=1, maxconn=DATABASE_MAX_CONNECTIONS, **db_params)

@contextmanager
def get_db_connection():
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

@app.route('/checkstock')
def check_stock():
    product = request.args.get("product")
    with tracer.start_as_current_span("StockController: Check Stock"):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                with tracer.start_as_current_span("DB: Check Product Stock"):
                    cursor.execute("SELECT stock_quantity FROM stock WHERE product = %s;", (product,))
                    stock = cursor.fetchone()
                    if stock:
                        custom_logger(f"Checked stock for product: {product}. Quantity: {stock[0]}.")
                        return jsonify({"product": product, "quantity": stock[0]})
                    custom_logger(f"Product: {product} not found in stock.", level='warning')
                    return jsonify({"error": "Product not found"}), 404

@app.route('/increasestock', methods=['POST'])
def increase_stock():
    product = request.json.get("product")
    quantity = request.json.get("quantity")
    with tracer.start_as_current_span("StockController: Increase Stock"):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                with tracer.start_as_current_span("DB: Increase Product Stock"):
                    cursor.execute("UPDATE stock SET stock_quantity = stock_quantity + %s WHERE product = %s;", (quantity, product))
                    conn.commit()
                    custom_logger(f"Increased stock for product: {product} by {quantity}.")
                    return jsonify({"message": "Stock increased successfully"})

@app.route('/decreasestock', methods=['POST'])
def decrease_stock():
    product = request.json.get("product")
    quantity = request.json.get("quantity")
    with tracer.start_as_current_span("StockController: Decrease Stock"):
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                with tracer.start_as_current_span("DB: Decrease Product Stock"):
                    cursor.execute("UPDATE stock SET stock_quantity = stock_quantity - %s WHERE product = %s;", (quantity, product))
                    conn.commit()
                    custom_logger(f"Decreased stock for product: {product} by {quantity}.")
                    return jsonify({"message": "Stock decreased successfully"})

if __name__ == "__main__":
    app.logger.info('Stock Controller is starting...')
    app.run(host="0.0.0.0", port=8081)

    # Close all connections in the pool when the app shuts down
    def shutdown():
        pool.closeall()
    import atexit
    atexit.register(shutdown)