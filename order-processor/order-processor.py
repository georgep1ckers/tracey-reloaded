from flask import Flask, jsonify, request
import logging
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
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
        "service.name": "order-processor",
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

# Instrument psycopg2
Psycopg2Instrumentor().instrument(skip_dep_check=True, enable_commenter=True)

# Database parameters:
db_params = {
    'dbname': "mydatabase",
    'user': "user",
    'password': "password",
    'host': "postgresql",
    'port': 5432,
}

# Set up a database connection pool
pool = SimpleConnectionPool(
    minconn=1, maxconn=DATABASE_MAX_CONNECTIONS, **db_params)

def get_db_connection():
    return pool.getconn()

def release_db_connection(conn):
    pool.putconn(conn)

@app.route('/checkorders')
def check_orders():
    with tracer.start_as_current_span("OrderProcessor: Check Orders"):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            with tracer.start_as_current_span("DB: Fetch Unprocessed Orders"):
                cursor.execute("SELECT order_id, cupboards, computers, chairs, desks FROM orders WHERE is_processed = FALSE;")
                orders = cursor.fetchall()
                response_data = [{"order_id":row[0], "cupboards": row[1], "computers": row[2], "chairs": row[3], "desks": row[4]} for row in orders]
            custom_logger(f"Fetched unprocessed orders: {response_data}",level='info')
            return jsonify(response_data)
        finally:
            cursor.close()
            release_db_connection(conn)

@app.route('/addorders', methods=['POST'])
def add_orders():
    with tracer.start_as_current_span("OrderProcessor: Add Orders"):
        order_data = request.get_json()
        order_id = order_data.get("order_id", 0)
        cupboards = order_data.get("cupboards", 0)
        computers = order_data.get("computers", 0)
        chairs = order_data.get("chairs", 0)
        desks = order_data.get("desks", 0)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            with tracer.start_as_current_span("DB: Insert New Order"):
                cursor.execute(
                    "INSERT INTO orders (cupboards, computers, chairs, desks) VALUES (%s, %s, %s, %s) RETURNING order_id;",
                    (cupboards, computers, chairs, desks)
                )
            order_id = cursor.fetchone()[0]
            custom_logger(f"Inserted new order with order_id: {order_id}",level='info')
            conn.commit()
            return jsonify({"message": "Order added successfully", "order_id": order_id}), 201
        finally:
            cursor.close()
            release_db_connection(conn)

@app.route('/deleteorders/<int:order_id>')
def delete_orders(order_id):
    with tracer.start_as_current_span("OrderProcessor: Delete Order"):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            with tracer.start_as_current_span("DB: Delete Order"):
                cursor.execute("DELETE FROM orders WHERE order_id = %s;", (order_id,))
            if cursor.rowcount == 0:
                custom_logger(f"No order found to delete.",level='error')
                return jsonify({"message": "Order not found"}), 404
            custom_logger(f"Deleted order with order_id: {order_id}",level='info')
            conn.commit()
            return jsonify({"message": f"Order {order_id} deleted successfully"}), 200
        finally:
            cursor.close()
            release_db_connection(conn)

if __name__ == "__main__":
    custom_logger(f"Processor is starting...",level='info')
    app.run(host="0.0.0.0", port=8080)

    # Close all connections in the pool when the app shuts down
    def shutdown():
        pool.closeall()
    import atexit
    atexit.register(shutdown)