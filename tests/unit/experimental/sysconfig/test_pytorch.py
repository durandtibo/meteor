import logging
from unittest.mock import patch

from pytest import LogCaptureFixture, mark
from torch.backends import cuda

from gravitorch.experimental.sysconfig import PyTorchCudaBackend

########################################
#     Tests for PyTorchCudaBackend     #
########################################


def test_pytorch_cuda_backend_str():
    assert str(PyTorchCudaBackend()).startswith("PyTorchCudaBackend(")


@mark.parametrize("allow_tf32", (True, False))
def test_pytorch_cuda_backend_allow_tf32(allow_tf32: bool):
    with PyTorchCudaBackend(allow_tf32=allow_tf32):
        assert cuda.matmul.allow_tf32 == allow_tf32


@mark.parametrize("allow_fp16_reduced_precision_reduction", (True, False))
def test_pytorch_cuda_backend_allow_fp16_reduced_precision_reduction(
    allow_fp16_reduced_precision_reduction: bool,
):
    with PyTorchCudaBackend(
        allow_fp16_reduced_precision_reduction=allow_fp16_reduced_precision_reduction
    ):
        assert (
            cuda.matmul.allow_fp16_reduced_precision_reduction
            == allow_fp16_reduced_precision_reduction
        )


@mark.parametrize("flash_sdp_enabled", (True, False))
def test_pytorch_cuda_backend_flash_sdp_enabled(flash_sdp_enabled: bool):
    with PyTorchCudaBackend(flash_sdp_enabled=flash_sdp_enabled):
        assert cuda.flash_sdp_enabled() == flash_sdp_enabled


@mark.parametrize("math_sdp_enabled", (True, False))
def test_pytorch_cuda_backend_math_sdp_enabled(math_sdp_enabled: bool):
    with PyTorchCudaBackend(math_sdp_enabled=math_sdp_enabled):
        assert cuda.math_sdp_enabled() == math_sdp_enabled


@mark.parametrize("preferred_linalg_backend", ("cusolver", "magma", "default"))
def test_pytorch_cuda_backend_preferred_linalg_backend(preferred_linalg_backend: str):
    with patch("torch.backends.cuda.preferred_linalg_library") as mock:
        with PyTorchCudaBackend(preferred_linalg_backend=preferred_linalg_backend):
            mock.assert_called()


@mark.parametrize("preferred_linalg_backend", ("cusolver", "magma", "default"))
def test_pytorch_cuda_backend_configure_preferred_linalg_backend(preferred_linalg_backend: str):
    with patch("torch.backends.cuda.preferred_linalg_library"):
        with PyTorchCudaBackend(preferred_linalg_backend=preferred_linalg_backend) as sysconfig:
            with patch("torch.backends.cuda.preferred_linalg_library") as mock:
                sysconfig.configure()
                mock.assert_called_once_with(preferred_linalg_backend)


def test_pytorch_cuda_backend_show(caplog: LogCaptureFixture):
    sysconfig = PyTorchCudaBackend()
    with caplog.at_level(logging.INFO):
        sysconfig.show()
        assert caplog.messages


def test_pytorch_cuda_backend_show_state_true(caplog: LogCaptureFixture):
    with PyTorchCudaBackend(show_state=True):
        assert caplog.messages


def test_pytorch_cuda_backend_show_state_false(caplog: LogCaptureFixture):
    with PyTorchCudaBackend():
        assert not caplog.messages
