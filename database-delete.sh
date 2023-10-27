#!/bin/bash

kubectl delete configmap postgresql-init

#  Delete db service
kubectl delete service postgresql

#  Delete db  deployment
kubectl delete deployment postgresql

#  Delete db persistant volume chain
kubectl delete pvc postgresql-pvc