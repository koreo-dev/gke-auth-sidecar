# GKE Auth Sidecar

Example Usage:

``` yaml
apiVersion: v1
kind: Pod
metadata:
  name: external-k8s
spec:
  serviceAccountName: external-k8s
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
      image: us-docker.pkg.dev/koreo-dev/koreo-dev/gke-auth-sidecar:latest
      env:
        - name: GKE_CLUSTER_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: clusterConfig
              key: endpoint # expects https://1.2.3.4
        - name: GKE_CLUSTER_CA
          valueFrom:
            secretKeyRef:
              name: clusterConfig
              key: ca.crt # expects certificate
        - name: KUBECONFIG_PATH
          value: /kube/config
      volumeMounts:
        - name: kubeconfig
          mountPath: /kube

  volumes:
    - name: kubeconfig
      emptyDir: {}
```
