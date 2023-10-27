#!/bin/bash

#  Create db configmap
kubectl apply -f database/postgresql-configmap.yaml


#  Create db persistant volume chain
kubectl apply -f database/postgresql-pvc.yaml

#  Create db deployment
kubectl apply -f database/postgresql-deployment.yaml

#  Create db service
kubectl apply -f database/postgresql-service.yaml