import time

import hivemind
import pytest
import torch
from test_utils import *

from petals.client import DistributedBloomConfig
from petals.data_structures import UID_DELIMITER
from petals.dht_utils import get_remote_sequence
from petals.server.handler import CACHE_TOKENS_AVAILABLE


@pytest.mark.forked
def test_server_info(block_from: int = 22, block_to: int = 24, max_length: int = 100, max_length2: int = 50):
    dht = hivemind.DHT(initial_peers=INITIAL_PEERS, client_mode=True, start=True)
    config = DistributedBloomConfig.from_pretrained(MODEL_NAME)

    blocks1 = get_remote_sequence(dht, block_from, block_to, config, f"{MODEL_NAME}{UID_DELIMITER}")
    blocks2 = get_remote_sequence(dht, block_to - 1, block_to, config, f"{MODEL_NAME}{UID_DELIMITER}")
    info_before = blocks1.sequence_manager.rpc_info

    with blocks1.inference_session(max_length=max_length) as sess:
        sess.step(torch.randn(1, 1, config.hidden_size))
        blocks1.sequence_manager._rpc_info = None  # invalidate cache
        info_inside = blocks1.sequence_manager.rpc_info

        with blocks2.inference_session(max_length=max_length2) as sess2:
            sess2.step(torch.randn(1, 1, config.hidden_size))
            blocks2.sequence_manager._rpc_info = None  # invalidate cache
            info_inside2 = blocks2.sequence_manager.rpc_info

    time.sleep(0.1)
    blocks1.sequence_manager._rpc_info = None  # invalidate cache
    info_after = blocks1.sequence_manager.rpc_info

    assert info_before[CACHE_TOKENS_AVAILABLE] == info_after[CACHE_TOKENS_AVAILABLE]
    assert info_before[CACHE_TOKENS_AVAILABLE] - info_inside[CACHE_TOKENS_AVAILABLE] == max_length * len(blocks1)
    assert info_inside[CACHE_TOKENS_AVAILABLE] - info_inside2[CACHE_TOKENS_AVAILABLE] == max_length2 * len(blocks2)
