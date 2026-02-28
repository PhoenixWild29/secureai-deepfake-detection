# Morpheus + Federated Learning Hybrid Design for SecureAI DeepFake Detection

This document captures the architectural and implementation updates added to this repository. The goal is to detect anomalies in streaming log data using the NVIDIA Morpheus framework combined with a federated learning (FL) coordinator for privacy‑preserving model updates.

## Overview
* **GPU‑accelerated streaming inference:** Morpheus connects to Kafka, performs GPU preprocessing with RAPIDS, runs models on Triton Inference Server, and emits scores in real time. 
* **Digital Fingerprinting:** Unsupervised anomaly detection workflow learns per‑entity baselines and flags deviations.
* **Federated Learning:** A Flower‑based coordinator aggregates model deltas from edge nodes without sharing raw data.

## Architecture
1. **Edge pipeline**
   * Collects logs/netflow/auth events into Kafka.
   * A Morpheus pipeline uses a featurizer to produce a 256‑dimensional `EVENT_TENSOR` and invokes the Triton **dfp_ensemble** model (encoder → autoencoder → post‑processing) to score anomalies.
   * Local mini‑batch training refreshes per‑identity baselines; model updates are sent to the FL coordinator.

2. **Federated coordinator**
   * A Flower `server.py` implements robust FedMedian aggregation and exposes Prometheus metrics.
   * Each `client.py` trains local models, sends updates, and exposes FL metrics.
   * K8s manifests and a Dockerfile are provided for containerized deployment.

3. **Core/SOC**
   * A Triton cluster serves both training and inference models.  
   * Morpheus pipelines correlate anomalies across sites and implement additional detectors (e.g. PII/SI leakage).

## Model Repository
The `triton_model_repository/` directory contains:

* `dfp_encoder/` – pretrained encoder with `config.pbtxt` specifying input/output tensors.
* `dfp_autoencoder/` – autoencoder for reconstruction error.
* `anomaly_postproc/` – Python model that computes anomaly scores from autoencoder outputs.
* `dfp_ensemble/` – Triton ensemble that chains the above models to minimize gRPC overhead.

## Flower FL Skeleton
Under `federated/`:

* `server.py` – Flower server with robust FedMedian aggregation and Prometheus metrics.
* `client.py` – Minimal NumPy client that trains local encoders and sends updates.
* `requirements.txt` and `Dockerfile` – environment definition for FL containers.
* `deployment.yaml` and `service.yaml` – K8s manifests for coordinator and clients.

## Monitoring & Dashboards
* **Prometheus** scrapes Triton, Kafka and FL metrics.  
* **Grafana dashboards**: `inference-latency.json` tracks Morpheus/Triton latencies; `fedmetrics.json` visualizes FL rounds, participating clients and loss.

## Development & Testing
* `morpheus_ext/featurizer.py` – turns common auth/netflow fields into the `EVENT_TENSOR` using categorical hashing and normalization.
* `scripts/synthetic_logs.py` – generates synthetic auth/log events with ~2 % anomalies for local testing.
* `docker-compose.yml` – composes Redpanda (Kafka), Triton, Morpheus app, FL coordinator, Prometheus and Grafana for a one‑command smoke test.  
  * Traefik or another reverse proxy can be added as needed.

## Deployment
* **Helm chart:** a `helm/` directory defines chart scaffolding with `Chart.yaml`, `values.yaml`, and templated deployments for Morpheus, Triton, Kafka, FL components, Prometheus and Grafana.
* **Terraform:** `infra/` contains modules for AWS EKS and GCP GKE clusters, GPU node pools, and Helm releases.
* **CI/CD:** GitHub Actions workflows build and push containers and deploy Helm releases via OIDC‑based authentication.

---

These additions provide a production‑ready starting point for detecting deepfake or anomalous events using the Morpheus framework and federated learning, with end‑to‑end orchestration via Kubernetes and Terraform. Feel free to extend or adapt the components for your specific use case.
