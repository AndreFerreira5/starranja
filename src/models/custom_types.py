from typing import Annotated, Any

from bson import Decimal128, ObjectId
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


def validate_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


# This custom type handles the conversion
PyObjectId = Annotated[
    str | ObjectId,
    # Validation: Convert string input to ObjectId
    BeforeValidator(validate_object_id),
    # Serialization: Convert ObjectId to string for JSON response
    PlainSerializer(lambda x: str(x), return_type=str),
    # Schema: Tell Swagger/OpenAPI this is a string
    WithJsonSchema({"type": "string", "example": "5eb7cf5a86d9755df3a6c593"}),
]


def validate_decimal128(v: Any) -> Decimal128:
    """
    Accepts str, float, int, or Decimal and converts to bson.Decimal128
    """
    if isinstance(v, Decimal128):
        return v
    try:
        # Convert input to string first to ensure precision, then to Decimal128
        return Decimal128(str(v))
    except Exception:
        raise ValueError("Invalid Decimal128 format")


def serialize_decimal128(v: Decimal128) -> str:
    """
    Converts bson.Decimal128 to string for JSON output.
    Using string preserves currency precision better than float.
    """
    return str(v)


PyDecimal128 = Annotated[
    Decimal128,
    # Validation: Input -> Decimal128
    BeforeValidator(validate_decimal128),
    # Serialization: Decimal128 -> String
    PlainSerializer(serialize_decimal128, return_type=str),
    # Schema: Documentation
    WithJsonSchema({"type": "string", "example": "100.00"}),
]
