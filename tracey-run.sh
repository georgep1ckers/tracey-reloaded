#!/bin/bash

#  Create tracey stock-controller deployment & service combined yaml
kubectl apply -f stock-controller.yaml

#  Create tracey processor deployment & service combined yaml
kubectl apply -f order-processor.yaml

#  Create tracey interface deployment yaml
kubectl apply -f warehouse-interface.yaml