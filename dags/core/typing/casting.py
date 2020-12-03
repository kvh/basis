from dataclasses import asdict
from enum import Enum
from functools import total_ordering

from dags.core.typing.object_schema import (
    ConflictBehavior,
    Field,
    ObjectSchema,
    create_quick_field,
    create_quick_schema,
)


@total_ordering
class CastToSchemaLevel(Enum):
    NONE = 0
    SOFT = 1
    HARD = 2

    def __lt__(self, other):
        return self.value < other.value


class SchemaTypeError(Exception):
    pass


def is_same_fieldtype_class(ft1: str, ft2: str) -> bool:
    # TODO: a lot to unpack and do here:
    #   When do we accept fieldtypes as compatible? when do we "downcast"?
    #   BigInteger vs Integer, Unicode(256) vs Unicode(128), etc
    #   What are the settings that let a user control this?
    return ft1.split("(")[0] == ft2.split("(")[0]


def is_strict_field_match(f1: Field, f2: Field) -> bool:
    return is_same_fieldtype_class(f1.field_type, f2.field_type) and f1.name == f2.name


def is_strict_schema_match(schema1: ObjectSchema, schema2: ObjectSchema) -> bool:
    if set(schema1.field_names()) != set(schema2.field_names()):
        return False
    for f1 in schema1.fields:
        f2 = schema2.get_field(f1.name)
        if not is_strict_field_match(f1, f2):
            return False
    return True


def has_subset_fields(sub: ObjectSchema, supr: ObjectSchema) -> bool:
    return set(sub.field_names()) <= set(supr.field_names())


def update_matching_field_definitions(
    schema: ObjectSchema, update_with_schema: ObjectSchema
) -> ObjectSchema:
    schema_dict = asdict(schema)
    fields = []
    for f in schema.fields:
        new_f = f
        try:
            new_f = update_with_schema.get_field(f.name)
        except NameError:
            pass
        fields.append(new_f)
    schema_dict["fields"] = fields
    return ObjectSchema.from_dict(schema_dict)


def cast_to_realized_schema(
    inferred_schema: ObjectSchema,
    nominal_schema: ObjectSchema,
    cast_level: CastToSchemaLevel = CastToSchemaLevel.SOFT,
):
    if is_strict_schema_match(inferred_schema, nominal_schema):
        return nominal_schema
    if has_subset_fields(nominal_schema, inferred_schema):
        if cast_level < CastToSchemaLevel.HARD:
            return update_matching_field_definitions(inferred_schema, nominal_schema)
        else:
            return nominal_schema
    else:
        if cast_level >= CastToSchemaLevel.NONE:
            raise SchemaTypeError(
                f"Inferred schema does not have necessary columns and cast level set to {cast_level}. "
                f"Inferred columns: {inferred_schema.field_names()}, "
                f"nominal columns: {nominal_schema.field_names()} "
            )
    return inferred_schema