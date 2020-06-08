from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Type

from basis.core.conversion.converter import (
    ConversionPath,
    Converter,
    ConverterLookup,
    StorageFormat,
)
from basis.core.data_block import StoredDataBlockMetadata
from basis.core.data_format import DataFormat
from basis.core.storage import Storage, StorageType
from basis.utils.common import printd

if TYPE_CHECKING:
    from basis.core.runnable import ExecutionContext


def get_converter_lookup() -> ConverterLookup:
    from basis.core.conversion.database_to_database import DatabaseToDatabaseConverter
    from basis.core.conversion.database_to_memory import DatabaseToMemoryConverter
    from basis.core.conversion.memory_to_database import MemoryToDatabaseConverter
    from basis.core.conversion.memory_to_memory import MemoryToMemoryConverter

    lookup = ConverterLookup()
    lookup.add(MemoryToDatabaseConverter)
    lookup.add(MemoryToMemoryConverter)
    lookup.add(DatabaseToMemoryConverter)
    lookup.add(DatabaseToDatabaseConverter)
    return lookup


def convert_lowest_cost(
    ctx: ExecutionContext,
    sdb: StoredDataBlockMetadata,
    target_storage: Storage,
    target_format: DataFormat,
):
    # TODO: cleanup target vs output
    target_storage_format = StorageFormat(target_storage.storage_type, target_format)
    cp = get_conversion_path_for_sdb(sdb, target_storage_format, ctx.all_storages)
    if cp is None:
        raise  # TODO
    return convert_sdb(ctx, sdb, cp)


def get_conversion_path_for_sdb(
    sdb: StoredDataBlockMetadata, target_format: StorageFormat, storages: List[Storage],
) -> Optional[ConversionPath]:
    source_format = StorageFormat(sdb.storage.storage_type, sdb.data_format)
    if source_format == target_format:
        # Already exists, do nothing
        return ConversionPath()
    conversion = (source_format, target_format)
    conversion_path = get_converter_lookup().get_lowest_cost_path(
        conversion, storages=storages,
    )
    return conversion_path


def convert_sdb(
    ctx: ExecutionContext,
    sdb: StoredDataBlockMetadata,
    conversion_path: ConversionPath,
):
    next_sdb = sdb
    for conversion_edge in conversion_path.conversions:
        conversion = conversion_edge.conversion
        target_storage_format = conversion[1]
        storage = select_storage(
            ctx.local_memory_storage, ctx.storages, target_storage_format
        )
        printd(
            "CONVERSION:", conversion[0], "->", conversion[1],
        )
        printd("\t", storage)
        printd("\t", next_sdb)
        next_sdb = conversion_edge.converter_class(ctx).convert(
            next_sdb, storage, target_storage_format.data_format
        )
    return next_sdb


def get_converter(
    sdb: StoredDataBlockMetadata, output_storage: Storage, output_format: DataFormat,
) -> Type[Converter]:
    target_format = StorageFormat(output_storage.storage_type, output_format)
    source_format = StorageFormat(sdb.storage.storage_type, sdb.data_format)
    conversion = (source_format, target_format)
    converter_class = get_converter_lookup().get_lowest_cost(conversion)
    if not converter_class:
        raise NotImplementedError(
            f"No converter to {target_format} from {source_format} for {sdb}"
        )
    return converter_class


def select_storage(
    local_memory_storage: Storage,
    storages: List[Storage],
    storage_format: StorageFormat,
) -> Storage:
    stype = storage_format.storage_type
    if stype == StorageType.DICT_MEMORY:
        return local_memory_storage
    for storage in storages:
        if stype == storage.storage_type:
            return storage
    raise Exception(f"No matching storage {storage_format}")