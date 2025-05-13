# GKE Auth Sidecar

Example Usage:

``` yaml
apiVersion: v1
kind: Pod
metadata:
  name: external-k8s
  namespace: skybit-systems-dev
spec:
  serviceAccountName: dev-workload-ksa
  containers:
    - name: app
      image: python:3.11
      command: ["sleep", "infinity"]
      volumeMounts:
        - name: kubeconfig
          mountPath: /kube
      env:
        - name: KUBECONFIG
          value: /kube/config

    - name: sidecar-auth
      image: us-docker.pkg.dev/koreo-dev/koreo-dev/gke-auth-sidecar:latest # Built from the Dockerfile we discussed
      env:
        - name: GKE_CLUSTER_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: dev
              key: endpoint
        - name: GKE_CLUSTER_CA
          valueFrom:
            secretKeyRef:
              name: dev
              key: ca.crt
        - name: KUBECONFIG_PATH
          value: /kube/config
      volumeMounts:
        - name: kubeconfig
          mountPath: /kube

  volumes:
    - name: kubeconfig
      emptyDir: {}
```
