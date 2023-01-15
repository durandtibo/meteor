import os
from unittest.mock import Mock, patch

from objectory import OBJECT_TARGET
from torch import nn
from torch.distributed.optim import ZeroRedundancyOptimizer
from torch.nn.parallel import DistributedDataParallel

from gravitorch import distributed as dist
from gravitorch.creators.optimizer import ZeroRedundancyOptimizerCreator
from gravitorch.distributed import Backend, auto_distributed_context
from tests.testing import gloo_available

####################################################
#     Tests for ZeroRedundancyOptimizerCreator     #
####################################################


@gloo_available
@patch.dict(
    os.environ,
    {
        dist.MASTER_ADDR: "127.0.0.1",
        dist.MASTER_PORT: "29530",
        dist.WORLD_SIZE: "1",
        dist.RANK: "0",
        dist.LOCAL_RANK: "0",
    },
    clear=True,
)
def test_zero_redundancy_optimizer_creator_create():
    creator = ZeroRedundancyOptimizerCreator(
        optimizer_config={OBJECT_TARGET: "torch.optim.SGD", "lr": 0.01}
    )
    with auto_distributed_context(dist_backend=Backend.GLOO):
        assert isinstance(
            creator.create(engine=Mock(), model=DistributedDataParallel(nn.Linear(4, 6))),
            ZeroRedundancyOptimizer,
        )