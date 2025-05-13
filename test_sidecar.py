import unittest
from unittest import mock
import subprocess
import os

import sidecar


class LoopBreakException(Exception):
    """Custom exception to break out of the main loop during tests."""

    pass


class TestSidecar(unittest.TestCase):

    @mock.patch("sidecar.logging.info")
    @mock.patch("sidecar.json.dump")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("sidecar.Path")
    def test_write_kubeconfig_success(
        self, mock_path_class, mock_open_file, mock_json_dump, mock_logging_info
    ):
        test_endpoint_val = "https://test-cluster.example.com"
        test_ca_cert = "TEST_CA_CERT_DATA"
        test_token = "TEST_TOKEN"
        test_path = "/fake/kube/config"

        # Setup mock for Path(path).parent.mkdir()
        mock_path_instance = mock.Mock()
        mock_path_class.return_value = mock_path_instance
        mock_parent_dir = mock.Mock()
        mock_path_instance.parent = mock_parent_dir

        sidecar.write_kubeconfig(test_endpoint_val, test_ca_cert, test_token, test_path)

        mock_path_class.assert_called_once_with(test_path)
        mock_parent_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_open_file.assert_called_once_with(test_path, "w")

        expected_kubeconfig = {
            "apiVersion": "v1",
            "clusters": [
                {
                    "cluster": {
                        "server": test_endpoint_val,
                        "certificate-authority-data": test_ca_cert,
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
            "users": [{"name": "external-user", "user": {"token": test_token}}],
        }
        mock_json_dump.assert_called_once_with(
            expected_kubeconfig, mock_open_file.return_value
        )
        mock_logging_info.assert_called_once_with("Updated kubeconfig with new token")

    @mock.patch("sidecar.subprocess.run")
    def test_fetch_token_success(self, mock_subprocess_run):
        expected_token = "fake_access_token"
        mock_completed_process = subprocess.CompletedProcess(
            args=["gcloud", "auth", "print-access-token"],
            returncode=0,
            stdout=f"  {expected_token}  \n",  # Test stripping of whitespace
            stderr="",
        )
        mock_subprocess_run.return_value = mock_completed_process

        token = sidecar.fetch_token()

        mock_subprocess_run.assert_called_once_with(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(token, expected_token)

    @mock.patch("sidecar.subprocess.run")
    def test_fetch_token_failure(self, mock_subprocess_run):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="gcloud auth print-access-token"
        )

        with self.assertRaises(subprocess.CalledProcessError):
            sidecar.fetch_token()

        mock_subprocess_run.assert_called_once_with(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("sidecar.logging.error")
    @mock.patch("sidecar.fetch_token")
    @mock.patch("sidecar.write_kubeconfig")
    @mock.patch("sidecar.time.sleep")  # To ensure it's not called
    def test_main_missing_env_vars(
        self, mock_time_sleep, mock_write_kubeconfig, mock_fetch_token, mock_log_error
    ):
        os.environ["GKE_CLUSTER_CA"] = "test_ca_data"

        sidecar.main()

        mock_log_error.assert_called_once_with(
            "Missing GKE_CLUSTER_ENDPOINT or GKE_CLUSTER_CA"
        )
        mock_fetch_token.assert_not_called()
        mock_write_kubeconfig.assert_not_called()
        mock_time_sleep.assert_not_called()

        mock_log_error.reset_mock()
        del os.environ["GKE_CLUSTER_CA"]

        os.environ["GKE_CLUSTER_ENDPOINT"] = "test_endpoint_data"

        sidecar.main()

        mock_log_error.assert_called_once_with(
            "Missing GKE_CLUSTER_ENDPOINT or GKE_CLUSTER_CA"
        )
        mock_fetch_token.assert_not_called()
        mock_write_kubeconfig.assert_not_called()
        mock_time_sleep.assert_not_called()

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("sidecar.logging.exception")
    @mock.patch("sidecar.logging.error")  # Ensure no regular errors logged
    @mock.patch("sidecar.fetch_token")
    @mock.patch("sidecar.write_kubeconfig")
    @mock.patch(
        "sidecar.time.sleep", side_effect=LoopBreakException
    )  # Break loop after one iteration
    def test_main_successful_run_one_iteration(
        self,
        mock_time_sleep,
        mock_write_kubeconfig,
        mock_fetch_token,
        mock_log_error,
        mock_log_exception,
    ):
        test_endpoint = "https://cluster.example.com"
        test_ca = "CA_DATA"
        test_kubeconfig_path = "/custom/path/kube.config"
        test_token = "fresh_token"

        os.environ["GKE_CLUSTER_ENDPOINT"] = test_endpoint
        os.environ["GKE_CLUSTER_CA"] = test_ca
        os.environ["KUBECONFIG_PATH"] = test_kubeconfig_path

        mock_fetch_token.return_value = test_token

        with self.assertRaises(LoopBreakException):
            sidecar.main()

        mock_fetch_token.assert_called_once()
        mock_write_kubeconfig.assert_called_once_with(
            test_endpoint, test_ca, test_token, test_kubeconfig_path
        )
        mock_time_sleep.assert_called_once_with(300)
        mock_log_error.assert_not_called()
        mock_log_exception.assert_not_called()

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("sidecar.logging.exception")
    @mock.patch("sidecar.fetch_token")
    @mock.patch("sidecar.write_kubeconfig")
    @mock.patch("sidecar.time.sleep", side_effect=LoopBreakException)
    def test_main_successful_run_default_kubeconfig_path(
        self,
        mock_time_sleep,
        mock_write_kubeconfig,
        mock_fetch_token,
        mock_log_exception,
    ):
        test_endpoint = "https://cluster.example.com"
        test_ca = "CA_DATA"
        test_token = "fresh_token"
        default_kubeconfig_path = "/kube/config"

        os.environ["GKE_CLUSTER_ENDPOINT"] = test_endpoint
        os.environ["GKE_CLUSTER_CA"] = test_ca

        mock_fetch_token.return_value = test_token

        with self.assertRaises(LoopBreakException):
            sidecar.main()

        mock_fetch_token.assert_called_once()
        mock_write_kubeconfig.assert_called_once_with(
            test_endpoint, test_ca, test_token, default_kubeconfig_path
        )
        mock_time_sleep.assert_called_once_with(300)
        mock_log_exception.assert_not_called()

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("sidecar.logging.exception")
    @mock.patch("sidecar.fetch_token")
    @mock.patch("sidecar.write_kubeconfig")
    @mock.patch("sidecar.time.sleep", side_effect=LoopBreakException)
    def test_main_fetch_token_exception(
        self,
        mock_time_sleep,
        mock_write_kubeconfig,
        mock_fetch_token,
        mock_log_exception,
    ):
        os.environ["GKE_CLUSTER_ENDPOINT"] = "https://cluster.example.com"
        os.environ["GKE_CLUSTER_CA"] = "CA_DATA"

        fetch_error = Exception("gcloud CLI error")
        mock_fetch_token.side_effect = fetch_error

        with self.assertRaises(LoopBreakException):
            sidecar.main()

        mock_fetch_token.assert_called_once()
        mock_write_kubeconfig.assert_not_called()
        mock_log_exception.assert_called_once_with("Failed to refresh kubeconfig")
        mock_time_sleep.assert_called_once_with(300)

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch("sidecar.logging.exception")
    @mock.patch("sidecar.fetch_token")
    @mock.patch("sidecar.write_kubeconfig")
    @mock.patch("sidecar.time.sleep", side_effect=LoopBreakException)
    def test_main_write_kubeconfig_exception(
        self,
        mock_time_sleep,
        mock_write_kubeconfig,
        mock_fetch_token,
        mock_log_exception,
    ):
        test_endpoint = "https://cluster.example.com"
        test_ca = "CA_DATA"
        test_token = "fresh_token"
        default_kubeconfig_path = "/kube/config"

        os.environ["GKE_CLUSTER_ENDPOINT"] = test_endpoint
        os.environ["GKE_CLUSTER_CA"] = test_ca

        mock_fetch_token.return_value = test_token
        write_error = Exception("Cannot write to file")
        mock_write_kubeconfig.side_effect = write_error

        with self.assertRaises(LoopBreakException):
            sidecar.main()

        mock_fetch_token.assert_called_once()
        mock_write_kubeconfig.assert_called_once_with(
            test_endpoint, test_ca, test_token, default_kubeconfig_path
        )
        mock_log_exception.assert_called_once_with("Failed to refresh kubeconfig")
        mock_time_sleep.assert_called_once_with(300)


if __name__ == "__main__":
    unittest.main()
