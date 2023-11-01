#!/bin/bash

# Create db configmap
kubectl apply -f tracey-database/postgresql-configmap.yaml

# Create db persistant volume chain
kubectl apply -f tracey-database/postgresql-pvc.yaml

# Create db deployment
kubectl apply -f tracey-database/postgresql-deployment.yaml

# Create db service
kubectl apply -f tracey-database/postgresql-service.yaml

# Wait for the database to be ready
echo "Waiting for database to be ready..."
kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s

# Once the database is ready, deploy the services
echo "Database is ready. Deploying services..."

# Create tracey stock-controller deployment & service combined yaml
kubectl apply -f stock-controller.yaml

# Create tracey processor deployment & service combined yaml
kubectl apply -f order-processor.yaml

# Create tracey interface deployment yaml
kubectl apply -f warehouse-interface.yaml

echo "Services deployed."