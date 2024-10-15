import inspect
import os
import types
from collections import deque
from copy import copy, deepcopy
from dataclasses import is_dataclass
from functools import lru_cache
from typing import Any, Deque, Dict, ForwardRef, FrozenSet, List, Mapping, Sequence, Set, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError
from pydantic._internal._typing_extra import eval_type_lenient as evaluate_forwardref
from pydantic._internal._utils import lenient_issubclass
from pydantic.fields import FieldInfo
from typing_extensions import Literal, get_args, get_origin

import frappeapi.params as params
from frappeapi.datastructures import ImmutableMultiDict
from frappeapi.exceptions import ErrorWrapper
from frappeapi.models import Dependant, ModelField, _regenerate_error_with_loc

sequence_annotation_to_type = {
	Sequence: list,
	List: list,
	list: list,
	Tuple: tuple,
	tuple: tuple,
	Set: set,
	set: set,
	FrozenSet: frozenset,
	frozenset: frozenset,
	Deque: deque,
	deque: deque,
}

sequence_types = tuple(sequence_annotation_to_type.keys())
UnionType = getattr(types, "UnionType", Union)

DefaultType = TypeVar("DefaultType")


class DefaultPlaceholder:
	def __init__(self, value: Any):
		self.value = value

	def __eq__(self, o: object) -> bool:
		return isinstance(o, DefaultPlaceholder) and self.value == o.value

	def __hash__(self) -> int:
		return hash(self.value)


def Default(value: Any):  # noqa: N802
	return DefaultPlaceholder(value)


def extract_endpoint_relative_path(func):
	full_path = inspect.getfile(func)
	path_parts = full_path.split(os.sep)
	try:
		apps_index = path_parts.index("apps") + 2
		sub_path_parts = path_parts[apps_index:]
		file_name = sub_path_parts[-1]
		sub_path_parts[-1] = os.path.splitext(file_name)[0]
		return ".".join(sub_path_parts)
	except ValueError:
		return None


def get_typed_annotation(annotation: Any, globalns: Dict[str, Any]) -> Any:
	if isinstance(annotation, str):
		annotation = ForwardRef(annotation)
		annotation = evaluate_forwardref(annotation, globalns, globalns)
	return annotation


def add_param_to_fields(*, field: ModelField, dependant: Dependant) -> None:
	field_info = field.field_info
	field_info_in = getattr(field_info, "in_", None)
	if field_info_in == params.ParamTypes.query:
		dependant.query_params.append(field)
	elif field_info_in == params.ParamTypes.header:
		dependant.header_params.append(field)
	else:
		assert (
			field_info_in == params.ParamTypes.cookie
		), f"non-body parameters must be in path, query, header or cookie: {field.name}"
		dependant.cookie_params.append(field)


def get_model_fields(model: Type[BaseModel]) -> List[ModelField]:
	return [ModelField(field_info=field_info, name=name) for name, field_info in model.model_fields.items()]


@lru_cache
def get_cached_model_fields(model: Type[BaseModel]) -> List[ModelField]:
	return get_model_fields(model)


def _annotation_is_sequence(annotation: Union[Type[Any], None]) -> bool:
	if lenient_issubclass(annotation, (str, bytes)):
		return False
	return lenient_issubclass(annotation, sequence_types)


def field_annotation_is_sequence(annotation: Union[Type[Any], None]) -> bool:
	origin = get_origin(annotation)
	if origin is Union or origin is UnionType:
		return any(field_annotation_is_sequence(arg) for arg in get_args(annotation))

	return _annotation_is_sequence(annotation) or _annotation_is_sequence(get_origin(annotation))


def is_sequence_field(field: ModelField) -> bool:
	return field_annotation_is_sequence(field.field_info.annotation)


def _get_multidict_value(field: ModelField, values: Mapping[str, Any], alias: Union[str, None] = None) -> Any:
	alias = alias or field.alias

	value = (
		values.getlist(alias)
		if is_sequence_field(field) and isinstance(values, ImmutableMultiDict)
		else values.get(alias, None)
	)

	if value is None or (is_sequence_field(field) and len(value) == 0):
		if field.required:
			return
		else:
			return deepcopy(field.default)
	return value


def get_missing_field_error(loc: Tuple[str, ...]) -> Dict[str, Any]:
	error = ValidationError.from_exception_data(
		"Field required", [{"type": "missing", "loc": loc, "input": {}}]
	).errors(include_url=False)[0]
	error["input"] = None
	return error  # type: ignore[return-value]


def _validate_value_with_model_field(
	*, field: ModelField, value: Any, values: Dict[str, Any], loc: Tuple[str, ...]
) -> Tuple[Any, List[Any]]:
	if value is None:
		if field.required:
			return None, [get_missing_field_error(loc=loc)]
		else:
			return deepcopy(field.default), []

	v_, errors_ = field.validate(value, values, loc=loc)
	if isinstance(errors_, ErrorWrapper):
		return None, [errors_]
	elif isinstance(errors_, list):
		new_errors = _regenerate_error_with_loc(errors=errors_, loc_prefix=())
		return None, new_errors
	else:
		return v_, []


def copy_field_info(*, field_info: FieldInfo, annotation: Any) -> FieldInfo:
	cls = type(field_info)
	merged_field_info = cls.from_annotation(annotation)
	new_field_info = copy(field_info)
	new_field_info.metadata = merged_field_info.metadata
	new_field_info.annotation = merged_field_info.annotation
	return new_field_info


def _annotation_is_complex(annotation: Union[Type[Any], None]) -> bool:
	return (
		lenient_issubclass(annotation, (BaseModel, Mapping))
		or _annotation_is_sequence(annotation)
		or is_dataclass(annotation)
	)


def field_annotation_is_complex(annotation: Union[Type[Any], None]) -> bool:
	origin = get_origin(annotation)
	if origin is Union or origin is UnionType:
		return any(field_annotation_is_complex(arg) for arg in get_args(annotation))

	return (
		_annotation_is_complex(annotation)
		or _annotation_is_complex(origin)
		or hasattr(origin, "__pydantic_core_schema__")
		or hasattr(origin, "__get_pydantic_core_schema__")
	)


def field_annotation_is_scalar(annotation: Any) -> bool:
	# handle Ellipsis here to make tuple[int, ...] work nicely
	return annotation is Ellipsis or not field_annotation_is_complex(annotation)


def is_scalar_field(field: ModelField) -> bool:
	from frappeapi import params

	return field_annotation_is_scalar(field.field_info.annotation) and not isinstance(field.field_info, params.Body)


def field_annotation_is_scalar_sequence(annotation: Union[Type[Any], None]) -> bool:
	origin = get_origin(annotation)
	if origin is Union or origin is UnionType:
		at_least_one_scalar_sequence = False
		for arg in get_args(annotation):
			if field_annotation_is_scalar_sequence(arg):
				at_least_one_scalar_sequence = True
				continue
			elif not field_annotation_is_scalar(arg):
				return False
		return at_least_one_scalar_sequence
	return field_annotation_is_sequence(annotation) and all(
		field_annotation_is_scalar(sub_annotation) for sub_annotation in get_args(annotation)
	)


def is_scalar_sequence_field(field: ModelField) -> bool:
	return field_annotation_is_scalar_sequence(field.field_info.annotation)


def _model_dump(model: BaseModel, mode: Literal["json", "python"] = "json", **kwargs: Any) -> Any:
	return model.model_dump(mode=mode, **kwargs)


def _get_model_config(model: BaseModel) -> Any:
	return model.model_config


def is_body_allowed_for_status_code(status_code: Union[int, str, None]) -> bool:
	if status_code is None:
		return True

	# Ref: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#patterned-fields-1
	if status_code in {
		"default",
		"1XX",
		"2XX",
		"3XX",
		"4XX",
		"5XX",
	}:
		return True

	current_status_code = int(status_code)
	return not (current_status_code < 200 or current_status_code in {204, 205, 304})
