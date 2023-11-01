#!/bin/bash

# Delete stock-controller deployment and service
kubectl delete deployment stock-controller
kubectl delete service stock-controller

# Delete order-processor deployment and service
kubectl delete deployment order-processor
kubectl delete service order-processor

# Delete warehouse-interface deployment
kubectl delete deployment warehouse-interface

# Wait for the deletion of the deployments to complete
kubectl wait --for=delete pod -l app=stock-controller --timeout=300s
kubectl wait --for=delete pod -l app=order-processor --timeout=300s
kubectl wait --for=delete pod -l app=warehouse-interface --timeout=300s

# Once the deployments are deleted, delete the database items
echo "Service containers removed. Deleting database items..."

# Delete configmap
kubectl delete configmap postgresql-init

# Delete db service
kubectl delete service postgresql

# Delete db deployment
kubectl delete deployment postgresql

# Delete db persistent volume claim
kubectl delete pvc postgresql-pvc

echo "Database items deleted."