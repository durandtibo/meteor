from gravitorch.distributed import Backend
from gravitorch.distributed import backend as dist_backend
from gravitorch.distributed import distributed_context, gloocontext, ncclcontext
from gravitorch.testing import (
    cuda_available,
    distributed_available,
    gloo_available,
    nccl_available,
)

########################################
#    Tests for distributed_context     #
########################################


@distributed_available
@gloo_available
def test_distributed_context_gloo() -> None:
    with distributed_context(Backend.GLOO):
        assert dist_backend() == Backend.GLOO
    assert dist_backend() is None


@distributed_available
@cuda_available
@nccl_available
def test_distributed_context_nccl() -> None:
    with distributed_context(Backend.NCCL):
        assert dist_backend() == Backend.NCCL
    assert dist_backend() is None


#################################
#     Tests for gloocontext     #
#################################


@distributed_available
@gloo_available
def test_gloocontext() -> None:
    with gloocontext():
        assert dist_backend() == Backend.GLOO
    assert dist_backend() is None


#################################
#     Tests for ncclcontext     #
#################################


@distributed_available
@cuda_available
@nccl_available
def test_ncclcontext() -> None:
    with ncclcontext():
        assert dist_backend() == Backend.NCCL
    assert dist_backend() is None
