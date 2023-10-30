#!/bin/bash

#  Create db configmap
kubectl apply -f tracey-database/postgresql-configmap.yaml

#  Create db persistant volume chain
kubectl apply -f tracey-database/postgresql-pvc.yaml

#  Create db deployment
kubectl apply -f tracey-database/postgresql-deployment.yaml

#  Create db service
kubectl apply -f tracey-database/postgresql-service.yaml