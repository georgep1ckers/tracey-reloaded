import requests
import time
import logging
import os
import random
import json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.trace import get_current_span
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace import Status, StatusCode

logging.basicConfig(level=logging.INFO)

def custom_logger(message, level='info'):
    current_span = get_current_span()
    if current_span.is_recording():
        trace_id = current_span.get_span_context().trace_id
        span_id = current_span.get_span_context().span_id
    else:
        trace_id = span_id = 'N/A'
        
    log_message = f"[TraceID: {trace_id}, SpanID: {span_id}] {message}"
    
    if level == 'info':
        logging.info(log_message)
    elif level == 'error':
        logging.error(log_message)
    elif level == 'warning':
        logging.warning(log_message)
    else:
        logging.debug(log_message)


# Get the local otel collector IP
OTEL_HOST = os.environ.get("OTEL_HOST", default="10.10.0.12:4317")
if not ":" in OTEL_HOST:
  OTEL_HOST = OTEL_HOST + ":4317"
print("OTEL Collector Address: {}".format(OTEL_HOST))

# Create OTLP exporter and point it to the OTEL Collector
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_HOST, insecure=True)

# Set OTEL service name and set the trace provider
resource = Resource(
    attributes={
        "service.name": "warehouse-interface",
        "version": "v0.0.1",
        "service.instance.id": "instance-1",
        "telemetry.sdk.name":"opentelemetry",
        "telemetry.sdk.language":"python",
        "telemetry.sdk.version":"1.19.0"
    }
)
trace.set_tracer_provider(TracerProvider(resource=resource))

# Set up BatchSpanProcessor and add it to the tracer provider
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Instrument requests
RequestsInstrumentor().instrument(
    span_kind=trace.SpanKind.CLIENT
)

tracer = trace.get_tracer(__name__)

# Instrumentation http status function
def set_http_status(http_status_code):
    if 200 <= http_status_code < 400:
        return Status(StatusCode.OK)
    else:
        return Status(StatusCode.ERROR, description=f"HTTP {http_status_code}")

def generate_random_order():
    """Generate a random order for products."""
    return {
        'computers': random.randint(1, 10),
        'chairs': random.randint(1, 10),
        'desks': random.randint(1, 10),
        'cupboards': random.randint(1, 10)
    }

def delete_order_from_order_processor(order_id):
    """Delete a processed order from the order-processor service."""
    with tracer.start_as_current_span("WarehouseInterface: Delete Order from Processor"):
        url = f"http://order-processor:8080/deleteorders/{order_id}"
#        headers = inject_tracer_to_request_headers({})
        response = requests.get(url)
        custom_logger(f"Attempting to delete order with ID: {order_id}",level='info')
        
        # Add additional span for HTTP response status
        with tracer.start_as_current_span("HTTP Response"):
            http_status_code = response.status_code
            current_span = get_current_span()
            current_span.set_attribute("http.status_code", http_status_code)
            current_span.set_status(set_http_status(http_status_code))

        if response.status_code != 200:
            custom_logger(f"Failed to delete order with ID: {order_id}",level='error')
            return None
        return response.json()

def get_order_from_order_processor():
    with tracer.start_as_current_span("WarehouseInterface: Get Order from Processor"):
        url = "http://order-processor:8080/checkorders"
        response = requests.get(url)
        custom_logger(f"Getting orders from Processor",level='info')

        # Add additional span for HTTP response status
        with tracer.start_as_current_span("HTTP Response"):
            http_status_code = response.status_code
            current_span = get_current_span()
            current_span.set_attribute("http.status_code", http_status_code)
            current_span.set_status(set_http_status(http_status_code))

        # Check the content type of the response
        content_type = response.headers.get('Content-Type')
        if 'application/json' in content_type:
            return response.json()
        else:
            custom_logger(f"Unexpected response content type: {content_type}. Content: {response.text}",level='error')
            return None


def add_order_to_order_processor(order_data):
    with tracer.start_as_current_span("WarehouseInterface: Add Order to Processor"):
        url = "http://order-processor:8080/addorders"
        
        response = requests.post(url, json=order_data)

        with tracer.start_as_current_span("HTTP Response"):
            http_status_code = response.status_code
            current_span = get_current_span()
            current_span.set_attribute("http.status_code", http_status_code)
            current_span.set_status(set_http_status(http_status_code))

        if response.status_code == 201:
            custom_logger(f"Order was added.",level='info')

        # Check if the response has content before attempting to parse it as JSON
        if response.text.strip():
            try:
                return response.json()
            except json.decoder.JSONDecodeError:
                custom_logger(f"Failed to decode JSON from response. Content: {response.text}",level='error')
                return None
        else:
            custom_logger(f"Received an empty response from the server.",level='warning')
            return None


def check_stock_from_stock_processor(product):
    with tracer.start_as_current_span("WarehouseInterface: Check Stock from stock-controller"):
        url = f"http://stock-controller:8081/checkstock?product={product}"
  #      headers = inject_tracer_to_request_headers({})
        response = requests.get(url)
        custom_logger(f"Checking stock for product {product}.",level='info')
        
        with tracer.start_as_current_span("HTTP Response"):
            http_status_code = response.status_code
            current_span = get_current_span()
            current_span.set_attribute("http.status_code", http_status_code)
            current_span.set_status(set_http_status(http_status_code))

        if response.status_code != 200:
            custom_logger(f"Failed to check stock for {product}.",level='error')
            return None
        return response.json()

def increase_stock_from_stock_processor(product, quantity):
    with tracer.start_as_current_span("WarehouseInterface: Increase Stock from stock-controller"):
        url = "http://stock-controller:8081/increasestock"
        data = {
            'product': product,
            'quantity': quantity
        }

        response = requests.post(url, json=data)
        custom_logger(f"Attempting to increase stock for {product} by {quantity}",level='info')

        
        with tracer.start_as_current_span("HTTP Response"):
            http_status_code = response.status_code
            current_span = get_current_span()
            current_span.set_attribute("http.status_code", http_status_code)
            current_span.set_status(set_http_status(http_status_code))

        if response.status_code != 200:
            custom_logger(f"Failed to increase stock for {product}",level='error')
            return None
        return response.json()

def decrease_stock_from_stock_processor(product, quantity):
    with tracer.start_as_current_span("WarehouseInterface: Decrease Stock from stock-controller"):
        url = "http://stock-controller:8081/decreasestock"
        data = {
            'product': product,
            'quantity': quantity
        }
#        headers = inject_tracer_to_request_headers({})
        response = requests.post(url, json=data)
        custom_logger(f"Attempting to decrease stock for {product} by {quantity}",level='info')
        
        with tracer.start_as_current_span("HTTP Response"):
            http_status_code = response.status_code
            current_span = get_current_span()
            current_span.set_attribute("http.status_code", http_status_code)
            current_span.set_status(set_http_status(http_status_code))

        if response.status_code != 200:
            custom_logger(f"Failed to decrease stock for {product}",level='error')
            return None
        return response.json()

if __name__ == "__main__":
    while True:
        # Generate a random order
        order = generate_random_order()
        
        # Add each product and its quantity to the order-processor
        add_order_to_order_processor(order)

        # Retrieve an unprocessed order
        response = get_order_from_order_processor()

        if response:
            if isinstance(response, list):
                # Assuming the first element contains what you need; adjust if needed
                first_order = response[0] if response else None
                order_id = first_order.get('order_id', None) if first_order else None
            elif isinstance(response, dict):
                order_id = response.get('order_id', None)
            else:
                custom_logger("Unknown response type",level='error')
                order_id = None

            if order_id:
                # Decrease stock after retrieving order
                for product, quantity in order.items():
                    stock_response = decrease_stock_from_stock_processor(product, quantity)
                    if stock_response and 'error' in stock_response:
                        logging.error(f"Failed to decrease stock for {product}")
                    else:
                        # Check current stock quantity after decrease
                        current_stock = check_stock_from_stock_processor(product)
                        if current_stock and current_stock['quantity'] < 100:
                            increase_stock_from_stock_processor(product, 100)
                        logging.info(f"Picked up order: {order_id} - {product} (Quantity: {quantity})")

                # Delete the order if it is processed
                delete_order_response = delete_order_from_order_processor(order_id)
                if delete_order_response:
                    custom_logger("Deleted processed order with ID: {order_id}",level='info')
            else:
                custom_logger("No order_id found in the response",level='error')
        else:
            custom_logger("No more orders to pick up",level='info')
        
        # Wait for 10 seconds before the next iteration
        time.sleep(10)