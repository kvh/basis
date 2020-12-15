from __future__ import annotations

from typing import Optional

import pytest
from pandas import DataFrame
from snapflow.core.data_block import Alias, DataBlock
from snapflow.core.data_formats import RecordsList
from snapflow.core.execution import (
    CompiledPipe,
    Executable,
    ExecutionManager,
    ExecutionSession,
    Worker,
)
from snapflow.core.graph import Graph
from snapflow.core.pipe_interface import NodeInterfaceManager
from snapflow.modules import core
from tests.utils import (
    TestSchema1,
    TestSchema4,
    make_test_env,
    make_test_run_context,
    pipe_generic,
    pipe_t1_sink,
    pipe_t1_source,
    pipe_t1_to_t2,
)

mock_dl_output = [{"f1": 2}, {"f2": 3}]


def pipe_dl_source() -> RecordsList[TestSchema4]:
    return mock_dl_output


def pipe_error() -> RecordsList[TestSchema4]:
    raise Exception("pipe FAIL")


def test_worker():
    env = make_test_env()
    g = Graph(env)
    rt = env.runtimes[0]
    ec = env.get_run_context(g, current_runtime=rt)
    with env.session_scope() as sess:
        node = g.create_node(key="node", pipe=pipe_t1_source)
        w = Worker(ec)
        dfi_mgr = NodeInterfaceManager(ec, sess, node)
        bdfi = dfi_mgr.get_bound_interface()
        r = Executable(
            node.key,
            CompiledPipe(node.pipe.key, node.pipe),
            bdfi,
        )
        run_result = w.execute(r)
        output = run_result.output_block
        assert output is None


def test_worker_output():
    env = make_test_env()
    env.add_module(core)
    g = Graph(env)
    env.add_storage("memory://test")
    with env.session_scope() as sess:
        rt = env.runtimes[0]
        ec = env.get_run_context(g, current_runtime=rt, target_storage=env.storages[0])
        output_alias = "node_output"
        node = g.create_node(key="node", pipe=pipe_dl_source, output_alias=output_alias)
        w = Worker(ec)
        dfi_mgr = NodeInterfaceManager(ec, sess, node)
        bdfi = dfi_mgr.get_bound_interface()
        r = Executable(
            node.key,
            CompiledPipe(node.pipe.key, node.pipe),
            bdfi,
        )
        run_result = w.execute(r)
        outputblock = run_result.output_block
        assert outputblock is not None
        outputblock = sess.merge(outputblock)
        block = outputblock.as_managed_data_block(ec, sess)
        assert block.as_records_list() == mock_dl_output
        assert block.nominal_schema is TestSchema4
        assert len(block.realized_schema.fields) == len(TestSchema4.fields)
        # Test alias was created correctly
        assert (
            sess.query(Alias).filter(Alias.alias == output_alias).first().data_block_id
            == block.data_block_id
        )


def test_non_terminating_pipe():
    def never_stop(input: Optional[DataBlock] = None) -> DataFrame:
        pass

    env = make_test_env()
    g = Graph(env)
    rt = env.runtimes[0]
    ec = env.get_run_context(g, current_runtime=rt)
    node = g.create_node(key="node", pipe=never_stop)
    em = ExecutionManager(ec)
    output = em.execute(node, to_exhaustion=True)
    assert output is None