from collections import OrderedDict
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm.exc import DetachedInstanceError

from snapflow.utils.common import cf, rand_str, title_to_snake_case, utcnow

SNAPFLOW_METADATA_TABLE_PREFIX = "_snapflow_"


class _BaseModel:
    @declared_attr
    def __tablename__(cls):
        return SNAPFLOW_METADATA_TABLE_PREFIX + title_to_snake_case(cls.__name__)  # type: ignore

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return self._repr()

    def _repr(self, **fields: Any) -> str:
        """
        Helper for __repr__
        From: https://stackoverflow.com/questions/55713664/sqlalchemy-best-way-to-define-repr-for-large-tables
        """
        field_strings = []
        at_least_one_attached_attribute = False
        for key, field in fields.items():
            try:
                from snapflow.core.typing.schema import Schema

                if isinstance(field, Schema):
                    field_strings.append(f"{key}={field.name}")
                elif key in ("id", "url"):
                    field_strings.append(str(cf.bold_italic(f"{key}={field!r}")))
                else:
                    field_strings.append(f"{key}={field!r}")
            except DetachedInstanceError:
                field_strings.append(f"{key}=DetachedInstanceError")
            else:
                at_least_one_attached_attribute = True
        if at_least_one_attached_attribute:
            # if len(field_strings) > 1:
            fields_string = ", ".join(field_strings)
            return f"<{self.__class__.__name__}({fields_string})>"
        return f"<{self.__class__.__name__} {id(self)}>"

    def _asdict(self):
        result = OrderedDict()
        for key in self.__mapper__.c.keys():  # type: ignore
            result[key] = getattr(self, key)
        return result


BaseModel = declarative_base(cls=_BaseModel)  # type: Any


id_counter: int = 0
last_second: str = ""


def timestamp_rand_key() -> str:
    """
    Ensure ids are generated uniquely and are monotonic in time.
    We add randomness to ensure we can handle separate processes.
    (This is not contradictory since any job dependency coordination will
    handle the risk that a separate process could generate a non-monotonic id --
    ie ids generated on separate processes have no risk of being mis-ordered, unless
    the jobs themselves are misordered)
    """
    global id_counter, last_second
    curr_second = utcnow().strftime("%y%m%d%H%M%S")
    if last_second != curr_second:
        id_counter = 0
    last_second = curr_second
    id_counter += 1
    # return rand_str(8).lower()
    return f"{curr_second}{id_counter:05}_{rand_str(3).lower()}"


### Custom type ideas. Not needed atm

# class JsonEncodedDict(TypeDecorator):
#     """Enables JSON storage by encoding and decoding on the fly."""
#
#     # json_type = MutableDict.as_mutable(JSONEncodedDict) For if you want mutability
#
#     impl = types.Unicode
#
#     def process_bind_param(self, value, dialect):
#         if value is not None:
#             value = json.dumps(value)
#         return value
#
#     def process_result_value(self, value, dialect):
#         if value is not None:
#             value = json.loads(value)
#         return value


# class Schema(TypeDecorator):
#     impl = types.Unicode
#
#     def process_bind_param(self, value: Union[Schema, str], dialect) -> str:
#         if value is None:
#             return None
#         if isinstance(value, str):
#             module, name = value.split(".")
#         else:
#             module = value.module
#             name = value.name
#         return f"{module}.{name}"
#
#     def process_result_value(self, value: str, dialect) -> str:
#         if value is None:
#             return None
#         return value
