from __future__ import annotations

from typing import Any, Iterator, List, Optional, Type, TypeVar

from snapflow.core.data_formats.base import (
    DataFormatBase,
    MemoryDataFormatBase,
    make_corresponding_iterator_format,
)
from sqlalchemy.engine import ResultProxy


class DatabaseCursorFormat(MemoryDataFormatBase):
    @classmethod
    def empty(cls):
        raise NotImplementedError

    @classmethod
    def type(cls) -> Type:
        return ResultProxy

    @classmethod
    def type_hint(cls):
        return "DatabaseCursor"

    @classmethod
    def copy_records(cls, obj: Any) -> Any:
        # Not applicable to cursor
        return obj


DatabaseCursor = TypeVar("DatabaseCursor", bound=ResultProxy)
DatabaseCursorIterator = Iterator[DatabaseCursor]

DatabaseCursorIteratorFormat = make_corresponding_iterator_format(DatabaseCursorFormat)
