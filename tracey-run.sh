#!/bin/bash

#  Create tracey stock-controller deployment
kubectl apply -f stock-controller-deployment.yaml

#  Create tracey stock-controller service
kubectl apply -f stock-controller-service.yaml

#  Create tracey processor deployment
kubectl apply -f order-processor-deployment.yaml

#  Create tracey processor service
kubectl apply -f order-processor-service.yaml

#  Create tracey interface deployment
kubectl apply -f warehouse-interface-deployment.yaml