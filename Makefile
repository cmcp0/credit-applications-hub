SHELL := /bin/bash
.DEFAULT_GOAL := help

APP_NAME ?= credit-apps
NAMESPACE ?= credit-apps
CHART ?= deploy/helm/credit-applications-hub
VALUES ?= $(CHART)/values.yaml
HELM_TIMEOUT ?= 15m
FAST_VALUES ?= $(CHART)/values-fast.yaml
FAST_HELM_TIMEOUT ?= 5m

PYTHON_IMAGE ?= credit-applications-hub-python:local
FRONTEND_IMAGE ?= credit-applications-hub-frontend:local

.PHONY: help \
	k8s-preflight k8s-context k8s-namespace k8s-events k8s-clean-fast-orphans \
	build-images helm-lint helm-template \
	deploy deploy-fast upgrade status \
	pods jobs services \
	logs-backend logs-webhooks logs-workers \
	restart-backend restart-workers \
	pf-backend pf-rabbitmq \
	undeploy

## Show available commands
help:
	@echo "Common commands:"
	@awk '\
		/^## / {desc = substr($$0, 4); next} \
		/^[a-zA-Z0-9_.-]+:/ { \
			if (desc != "") { \
				split($$1, a, ":"); \
				printf "  %-30s %s\n", a[1], desc; \
				desc = ""; \
			} \
		}' $(MAKEFILE_LIST)

## Verify kube context and API server reachability
k8s-preflight:
	@kubectl config current-context
	@kubectl cluster-info

## Show configured Kubernetes contexts
k8s-context:
	@kubectl config get-contexts

## Ensure namespace exists
k8s-namespace:
	@kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -

## Remove orphaned non-fast resources when switching profiles
k8s-clean-fast-orphans:
	@kubectl delete deploy -n $(NAMESPACE) \
		$(APP_NAME)-credit-applications-hub-webhooks \
		$(APP_NAME)-credit-applications-hub-mock-provider \
		$(APP_NAME)-credit-applications-hub-redis \
		$(APP_NAME)-credit-applications-hub-rabbitmq \
		--ignore-not-found
	@kubectl delete svc -n $(NAMESPACE) \
		$(APP_NAME)-credit-applications-hub-webhooks \
		$(APP_NAME)-credit-applications-hub-mock-provider \
		$(APP_NAME)-credit-applications-hub-redis \
		$(APP_NAME)-credit-applications-hub-rabbitmq \
		--ignore-not-found
	@kubectl get deploy -n $(NAMESPACE) -o name | grep "$(APP_NAME)-credit-applications-hub-worker-" | xargs -r kubectl delete -n $(NAMESPACE) || true
	@kubectl delete pvc -n $(NAMESPACE) \
		$(APP_NAME)-credit-applications-hub-postgres-data \
		$(APP_NAME)-credit-applications-hub-rabbitmq-data \
		--ignore-not-found

## Build local images used by Helm chart
build-images:
	docker build -f deploy/docker/python.Dockerfile -t $(PYTHON_IMAGE) .
	docker build -f deploy/docker/frontend.Dockerfile -t $(FRONTEND_IMAGE) .

## Lint Helm chart
helm-lint:
	helm lint $(CHART)

## Render Helm manifests locally
helm-template:
	helm template $(APP_NAME) $(CHART) --namespace $(NAMESPACE) --values $(VALUES)

## Deploy/upgrade stack with Helm
deploy: k8s-namespace
	helm upgrade --install $(APP_NAME) $(CHART) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait \
		--timeout $(HELM_TIMEOUT)

## Fast deploy (<5m target) using reduced profile (fresh reinstall)
deploy-fast: k8s-namespace
	@echo "Reinstalling $(APP_NAME) for clean fast profile (previous release resources/data are removed)."
	@helm uninstall $(APP_NAME) -n $(NAMESPACE) --ignore-not-found
	@$(MAKE) k8s-clean-fast-orphans
	helm upgrade --install $(APP_NAME) $(CHART) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--values $(VALUES) \
		--values $(FAST_VALUES) \
		--wait \
		--timeout $(FAST_HELM_TIMEOUT)

## Alias for deploy
upgrade: deploy

## Show Helm release status and key Kubernetes resources
status:
	@helm status $(APP_NAME) -n $(NAMESPACE)
	@echo
	@kubectl get pods -n $(NAMESPACE)
	@echo
	@kubectl get jobs -n $(NAMESPACE)
	@echo
	@kubectl get svc -n $(NAMESPACE)

## Show pods in namespace
pods:
	kubectl get pods -n $(NAMESPACE)

## Show jobs in namespace
jobs:
	kubectl get jobs -n $(NAMESPACE)

## Show services in namespace
services:
	kubectl get svc -n $(NAMESPACE)

## Tail backend deployment logs
logs-backend:
	kubectl logs -n $(NAMESPACE) deploy/$(APP_NAME)-credit-applications-hub-backend -f

## Tail webhooks deployment logs
logs-webhooks:
	kubectl logs -n $(NAMESPACE) deploy/$(APP_NAME)-credit-applications-hub-webhooks -f

## Show recent logs for all worker deployments
logs-workers:
	@kubectl get deploy -n $(NAMESPACE) -o name | grep 'worker-' | while read -r d; do \
		echo "==== $$d ===="; \
		kubectl logs -n $(NAMESPACE) "$$d" --tail=80 || true; \
		echo; \
	done

## Restart backend deployment
restart-backend:
	kubectl rollout restart deploy/$(APP_NAME)-credit-applications-hub-backend -n $(NAMESPACE)
	kubectl rollout status deploy/$(APP_NAME)-credit-applications-hub-backend -n $(NAMESPACE)

## Restart all worker deployments
restart-workers:
	@kubectl get deploy -n $(NAMESPACE) -o name | grep 'worker-' | xargs -r kubectl rollout restart -n $(NAMESPACE)
	@kubectl get deploy -n $(NAMESPACE) -o name | grep 'worker-' | xargs -r -n1 kubectl rollout status -n $(NAMESPACE)

## Show recent namespace events
k8s-events:
	kubectl get events -n $(NAMESPACE) --sort-by=.metadata.creationTimestamp

## Port-forward backend service to localhost:8000
pf-backend:
	kubectl port-forward -n $(NAMESPACE) svc/$(APP_NAME)-credit-applications-hub-backend 8000:8000

## Port-forward RabbitMQ management UI to localhost:15672
pf-rabbitmq:
	kubectl port-forward -n $(NAMESPACE) svc/$(APP_NAME)-credit-applications-hub-rabbitmq 15672:15672

## Remove Helm release from namespace
undeploy:
	helm uninstall $(APP_NAME) -n $(NAMESPACE)
