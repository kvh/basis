from __future__ import annotations

import tempfile
from typing import Any, Dict, Optional

from pandas import DataFrame
from sqlalchemy.orm import Session

from dags import DataBlock, Environment, Graph, Pipe, Storage
from dags.core.module import DagsModule
from dags.core.node import DataBlockLog, Node, PipeLog
from dags.core.typing.inference import infer_schema_from_records_list
from dags.utils.common import rand_str
from dags.utils.data import read_csv, read_json, read_raw_string_csv
from dags.utils.pandas import records_list_to_dataframe


def get_tmp_sqlite_db_url(dbname=None):
    if dbname is None:
        dbname = rand_str(10)
    dir = tempfile.mkdtemp()
    return f"sqlite:///{dir}/{dbname}.db"


def display_pipe_log(sess: Session):
    for dbl in sess.query(DataBlockLog).order_by(DataBlockLog.created_at):
        print(f"{dbl.pipe_log.pipe_key:30} {dbl.data_block_id:4} {dbl.direction}")


def str_as_dataframe(test_data: str, module: Optional[DagsModule] = None) -> DataFrame:
    # TODO: add conform_dataframe_to_schema option
    if test_data.endswith(".csv"):
        if module is None:
            raise
        with module.open_module_file(test_data) as f:
            raw_records = read_csv(f.readlines())
    elif test_data.endswith(".json"):
        if module is None:
            raise
        with module.open_module_file(test_data) as f:
            raw_records = [read_json(line) for line in f]
    else:
        # Raw str csv
        raw_records = read_raw_string_csv(test_data)
    auto_schema = infer_schema_from_records_list(raw_records)
    df = records_list_to_dataframe(raw_records, auto_schema)
    return df


def produce_pipe_output_for_static_input(
    pipe: Pipe,
    config: Dict[str, Any] = None,
    input: Any = None,
    upstream: Any = None,
    env: Optional[Environment] = None,
    module: Optional[DagsModule] = None,
    target_storage: Optional[Storage] = None,
) -> Optional[DataBlock]:
    input = input or upstream
    if env is None:
        db = get_tmp_sqlite_db_url()
        env = Environment(metadata_storage=db)
    if target_storage:
        target_storage = env.add_storage(target_storage)
    g = Graph(env)
    input_dfs = {}
    input_nodes = {}
    pi = pipe.get_interface(env)
    if isinstance(input, str):
        assert len(pi.get_non_recursive_inputs()) == 1
        input = {pi.get_non_recursive_inputs()[0].name: input}
    for n, inp in input.items():
        input_dfs[n] = str_as_dataframe(inp, module)
    for input in pi.inputs:
        if input.is_self_ref:
            continue
        assert input.name is not None
        input_df = input_dfs[input.name]
        n = g.add_node(
            f"_input_{input.name}",
            "core.extract_dataframe",
            config={"dataframe": input_df},
        )
        input_nodes[input.name] = n
    test_node = g.add_node(f"{pipe.name}", pipe, config=config, inputs=input_nodes)
    return env.produce(g, test_node, to_exhaustion=False, target_storage=target_storage)
