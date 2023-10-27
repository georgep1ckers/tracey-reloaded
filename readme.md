# Tracey Reloaded

Tracey Reloaded is a dummy Kubernetes-based application designed to generate logs, metrics and traces for a 'simulated' warehouse operations. It is intended to be used with OpenTelemetry for the collection of telemetry data and shipping on to Coralogix. The application consists of multiple services: 

- **Warehouse Interface**
- **Order Processor**
- **Stock Processor**
- **PostgreSQL Database**


## Prerequisites

- Kubernetes cluster up and running.
- `kubectl` command-line tool installed and configured to communicate with your cluster.

## Deployment

1. **Start the PostgreSQL Database**

   Execute the following script:
   ```
   ./database-run.sh
   ```

2. **Deploy the Services**

   Execute the following script:
   ```
   ./tracey-run.sh
   ```

## Deletion

If you wish to remove the services and the database from your Kubernetes cluster:

1. **Delete the Services**

   Execute the following script:
   ```
   ./tracey-delete.sh
   ```

2. **Delete the PostgreSQL Database**

   Execute the following script:
   ```
   ./database-delete.sh
   ```

## Contributing

For contributions, please ensure you are an authorized contributor to this repository and then create a pull request or raise an issue.