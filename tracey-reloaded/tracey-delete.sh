#!/bin/bash

#  Create stock-controller deployment
kubectl delete deployment stock-controller

#  Create stock-controller service
kubectl delete service stock-controller

#  Create order-processor deployment
kubectl delete deployment order-processor

#  Create order-processor service
kubectl delete service order-processor

#  Create tracey picker deployment
kubectl delete deployment warehouse-interface