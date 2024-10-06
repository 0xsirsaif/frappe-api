from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import AliasChoices, AliasPath, AnyUrl
from pydantic.fields import FieldInfo
from pydantic.version import VERSION
from pydantic_core import PydanticUndefined
from typing_extensions import TypedDict, deprecated

Undefined = PydanticUndefined
_Unset: Any = Undefined

PYDANTIC_VERSION = VERSION


class Example(TypedDict, total=False):
	summary: Optional[str]
	description: Optional[str]
	value: Optional[Any]
	externalValue: Optional[AnyUrl]

	__pydantic_config__ = {"extra": "allow"}


class ParamTypes(Enum):
	query = "query"
	header = "header"
	path = "path"
	cookie = "cookie"


class Param(FieldInfo):
	in_: ParamTypes

	def __init__(
		self,
		default: Any = Undefined,
		*,
		default_factory: Union[Callable[[], Any], None] = _Unset,
		annotation: Optional[Any] = None,
		alias: Optional[str] = None,
		alias_priority: Union[int, None] = _Unset,
		validation_alias: str | AliasPath | AliasChoices | None = None,
		serialization_alias: str | AliasPath | AliasChoices | None = None,
		title: Optional[str] = None,
		description: Optional[str] = None,
		gt: Optional[float] = None,
		ge: Optional[float] = None,
		lt: Optional[float] = None,
		le: Optional[float] = None,
		min_length: Optional[int] = None,
		max_length: Optional[int] = None,
		pattern: Optional[str] = None,
		discriminator: Union[str, None] = None,
		strict: Union[bool, None] = _Unset,
		multiple_of: Union[float, None] = _Unset,
		allow_inf_nan: Union[bool, None] = _Unset,
		max_digits: Union[int, None] = _Unset,
		decimal_places: Union[int, None] = _Unset,
		examples: Optional[List[Any]] = None,
		openapi_examples: Optional[Dict[str, Example]] = None,
		deprecated: Union[deprecated, str, bool, None] = None,
		include_in_schema: bool = True,
		json_schema_extra: Union[Dict[str, Any], None] = None,
		**extra: Any,
	):
		self.include_in_schema = include_in_schema
		self.openapi_examples = openapi_examples
		current_json_schema_extra = json_schema_extra or extra

		kwargs = dict(
			default=default,
			default_factory=default_factory,
			alias=alias,
			title=title,
			description=description,
			gt=gt,
			ge=ge,
			lt=lt,
			le=le,
			min_length=min_length,
			max_length=max_length,
			discriminator=discriminator,
			multiple_of=multiple_of,
			allow_inf_nan=allow_inf_nan,
			max_digits=max_digits,
			decimal_places=decimal_places,
			examples=examples,
			annotation=annotation,
			alias_priority=alias_priority,
			validation_alias=validation_alias,
			serialization_alias=serialization_alias,
			strict=strict,
			json_schema_extra=current_json_schema_extra,
			pattern=pattern,
			**extra,
		)

		if PYDANTIC_VERSION < "2.7.0":
			self.deprecated = deprecated
		else:
			kwargs["deprecated"] = deprecated

		use_kwargs = {k: v for k, v in kwargs.items() if v is not _Unset}

		super().__init__(**use_kwargs)

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.default})"


class Query(Param):
	in_ = ParamTypes.query

	def __init__(
		self,
		default: Any = Undefined,
		*,
		default_factory: Union[Callable[[], Any], None] = _Unset,
		annotation: Optional[Any] = None,
		alias: Optional[str] = None,
		alias_priority: Union[int, None] = _Unset,
		validation_alias: str | AliasPath | AliasChoices | None = None,
		serialization_alias: str | AliasPath | AliasChoices | None = None,
		title: Optional[str] = None,
		description: Optional[str] = None,
		gt: Optional[float] = None,
		ge: Optional[float] = None,
		lt: Optional[float] = None,
		le: Optional[float] = None,
		min_length: Optional[int] = None,
		max_length: Optional[int] = None,
		pattern: Optional[str] = None,
		discriminator: Union[str, None] = None,
		strict: Union[bool, None] = _Unset,
		multiple_of: Union[float, None] = _Unset,
		allow_inf_nan: Union[bool, None] = _Unset,
		max_digits: Union[int, None] = _Unset,
		decimal_places: Union[int, None] = _Unset,
		examples: Optional[List[Any]] = None,
		openapi_examples: Optional[Dict[str, Example]] = None,
		deprecated: Union[deprecated, str, bool, None] = None,
		include_in_schema: bool = True,
		json_schema_extra: Union[Dict[str, Any], None] = None,
		**extra: Any,
	):
		super().__init__(
			default=default,
			default_factory=default_factory,
			annotation=annotation,
			alias=alias,
			alias_priority=alias_priority,
			validation_alias=validation_alias,
			serialization_alias=serialization_alias,
			title=title,
			description=description,
			gt=gt,
			ge=ge,
			lt=lt,
			le=le,
			min_length=min_length,
			max_length=max_length,
			pattern=pattern,
			discriminator=discriminator,
			strict=strict,
			multiple_of=multiple_of,
			allow_inf_nan=allow_inf_nan,
			max_digits=max_digits,
			decimal_places=decimal_places,
			deprecated=deprecated,
			examples=examples,
			openapi_examples=openapi_examples,
			include_in_schema=include_in_schema,
			json_schema_extra=json_schema_extra,
			**extra,
		)
