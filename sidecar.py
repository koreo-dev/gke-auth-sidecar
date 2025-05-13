import os
import subprocess
import time
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)


def write_kubeconfig(endpoint: str, ca_cert: str, token: str, path: str):
    kubeconfig = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "server": endpoint,
                    "certificate-authority-data": ca_cert,
                },
                "name": "external-cluster",
            }
        ],
        "contexts": [
            {
                "context": {"cluster": "external-cluster", "user": "external-user"},
                "name": "external-context",
            }
        ],
        "current-context": "external-context",
        "kind": "Config",
        "users": [{"name": "external-user", "user": {"token": token}}],
    }

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(kubeconfig, f)
    logging.info("Updated kubeconfig with new token")


def fetch_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main():
    endpoint = os.environ.get("GKE_CLUSTER_ENDPOINT")
    ca_cert = os.environ.get("GKE_CLUSTER_CA")
    kubeconfig_path = os.environ.get("KUBECONFIG_PATH", "/kube/config")

    if not endpoint or not ca_cert:
        logging.error("Missing GKE_CLUSTER_ENDPOINT or GKE_CLUSTER_CA")
        return

    while True:
        try:
            token = fetch_token()
            write_kubeconfig(endpoint, ca_cert, token, kubeconfig_path)
        except Exception as e:
            logging.exception("Failed to refresh kubeconfig")
        time.sleep(300)  # refresh every 5 minutes


if __name__ == "__main__":
    main()
