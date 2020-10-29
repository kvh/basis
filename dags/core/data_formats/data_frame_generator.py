from __future__ import annotations

from collections import abc
from typing import TYPE_CHECKING, Any, Optional, Type

import pandas as pd

from dags.core.data_formats.base import MemoryDataFormatBase, ReusableGenerator

if TYPE_CHECKING:
    from dags.core.data_block import LocalMemoryDataRecords
    from dags.core.typing.object_schema import SchemaMapping, ObjectSchema


class DataFrameGenerator(ReusableGenerator[pd.DataFrame]):
    pass


class DataFrameGeneratorFormat(MemoryDataFormatBase):
    @classmethod
    def type(cls) -> Type:
        return DataFrameGenerator

    @classmethod
    def maybe_instance(cls, obj: Any) -> bool:
        return isinstance(obj, abc.Generator)

    @classmethod
    def definitely_instance(cls, obj: Any) -> bool:
        return isinstance(obj, cls.type())

    @classmethod
    def infer_schema_from_records(cls, records: DataFrameGenerator) -> ObjectSchema:
        from dags.core.typing.inference import infer_schema_from_records_list
        from dags.core.data_formats import get_records_list_sample

        dl = get_records_list_sample(records)
        if dl is None:
            raise ValueError("Empty records object")
        inferred_schema = infer_schema_from_records_list(dl)
        return inferred_schema

    @classmethod
    def conform_records_to_schema(
        cls, records: DataFrameGenerator
    ) -> DataFrameGenerator:
        raise NotImplementedError

    @classmethod
    def apply_schema_mapping(
        cls, mapping: SchemaMapping, dfg: DataFrameGenerator
    ) -> DataFrameGenerator:
        for df in dfg:
            yield df.rename(mapping.as_dict(), axis=1)