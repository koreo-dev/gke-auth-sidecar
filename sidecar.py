import os
import json
from pathlib import Path
import time
import logging
import subprocess

logging.basicConfig(level=logging.INFO)

def get_gcp_token():
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get GCP token: {e.stderr}")
        raise

def main():
    endpoint = os.environ.get("GKE_CLUSTER_ENDPOINT")
    ca_cert = os.environ.get("GKE_CLUSTER_CA")
    kubeconfig_path = os.environ.get("KUBECONFIG_PATH", "/kube/config")

    if not endpoint or not ca_cert:
        logging.error("Missing endpoint or CA cert env vars")
        return

    logging.info(f"Using endpoint: {endpoint}")
    logging.info(f"Writing kubeconfig to: {kubeconfig_path}")

    Path("/kube").mkdir(parents=True, exist_ok=True)

    token = get_gcp_token()

    kubeconfig = {
        "apiVersion": "v1",
        "clusters": [{
            "cluster": {
                "server": endpoint,
                "certificate-authority-data": ca_cert
            },
            "name": "external-cluster"
        }],
        "contexts": [{
            "context": {
                "cluster": "external-cluster",
                "user": "external-user"
            },
            "name": "external-context"
        }],
        "current-context": "external-context",
        "kind": "Config",
        "users": [{
            "name": "external-user",
            "user": {
                "token": token
            }
        }]
    }

    with open(kubeconfig_path, "w") as f:
        json.dump(kubeconfig, f)
        logging.info("Wrote kubeconfig with token")

    # Stay alive to allow refresh later if needed
    while True:
        time.sleep(300)

if __name__ == "__main__":
    main()
