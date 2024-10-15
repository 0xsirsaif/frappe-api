from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

from openapi_pydantic_v2 import SecurityRequirement
from pydantic import TypeAdapter, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined, PydanticUndefinedType as PydanticUndefinedType
from typing_extensions import Literal
from werkzeug.wrappers import Response as WerkzeugResponse

Required = PydanticUndefined
Undefined = PydanticUndefined
UndefinedType = PydanticUndefinedType
Validator = Any
Validator = Any
IncEx = Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any]]


class BaseConfig:
	pass


def _regenerate_error_with_loc(
	*, errors: Sequence[Any], loc_prefix: Tuple[Union[str, int], ...]
) -> List[Dict[str, Any]]:
	updated_loc_errors: List[Any] = [{**err, "loc": loc_prefix + err.get("loc", ())} for err in errors]

	return updated_loc_errors


@dataclass
class ModelField:
	field_info: FieldInfo
	name: str
	mode: Literal["validation", "serialization"] = "validation"

	@property
	def alias(self) -> str:
		a = self.field_info.alias
		return a if a is not None else self.name

	@property
	def required(self) -> bool:
		return self.field_info.is_required()

	@property
	def default(self) -> Any:
		return self.get_default()

	@property
	def type_(self) -> Any:
		return self.field_info.annotation

	def __post_init__(self) -> None:
		self._type_adapter: TypeAdapter[Any] = TypeAdapter(Annotated[self.field_info.annotation, self.field_info])

	def get_default(self) -> Any:
		if self.field_info.is_required():
			return Undefined
		return self.field_info.get_default(call_default_factory=True)

	def validate(
		self,
		value: Any,
		values: Dict[str, Any] = {},  # noqa: B006
		*,
		loc: Tuple[Union[int, str], ...] = (),
	) -> Tuple[Any, Union[List[Dict[str, Any]], None]]:
		try:
			return (
				self._type_adapter.validate_python(value, from_attributes=True),
				None,
			)
		except ValidationError as exc:
			return None, _regenerate_error_with_loc(errors=exc.errors(include_url=False), loc_prefix=loc)

	def serialize(
		self,
		value: Any,
		*,
		mode: Literal["json", "python"] = "json",
		include: Union[IncEx, None] = None,
		exclude: Union[IncEx, None] = None,
		by_alias: bool = True,
		exclude_unset: bool = False,
		exclude_defaults: bool = False,
		exclude_none: bool = False,
	) -> Any:
		# What calls this code passes a value that already called
		# self._type_adapter.validate_python(value)
		return self._type_adapter.dump_python(
			value,
			mode=mode,
			include=include,
			exclude=exclude,
			by_alias=by_alias,
			exclude_unset=exclude_unset,
			exclude_defaults=exclude_defaults,
			exclude_none=exclude_none,
		)

	def __hash__(self) -> int:
		# Each ModelField is unique for our purposes, to allow making a dict from
		# ModelField to its JSON Schema.
		return id(self)


@dataclass
class Dependant:
	path_params: List[ModelField] = field(default_factory=list)
	query_params: List[ModelField] = field(default_factory=list)
	header_params: List[ModelField] = field(default_factory=list)
	cookie_params: List[ModelField] = field(default_factory=list)
	body_params: List[ModelField] = field(default_factory=list)
	dependencies: List["Dependant"] = field(default_factory=list)
	security_requirements: List[SecurityRequirement] = field(default_factory=list)
	name: Optional[str] = None
	call: Optional[Callable[..., Any]] = None
	request_param_name: Optional[str] = None
	websocket_param_name: Optional[str] = None
	http_connection_param_name: Optional[str] = None
	response_param_name: Optional[str] = None
	background_tasks_param_name: Optional[str] = None
	security_scopes_param_name: Optional[str] = None
	security_scopes: Optional[List[str]] = None
	use_cache: bool = True
	path: Optional[str] = None
	cache_key: Tuple[Optional[Callable[..., Any]], Tuple[str, ...]] = field(init=False)

	def __post_init__(self) -> None:
		self.cache_key = (self.call, tuple(sorted(set(self.security_scopes or []))))


@dataclass
class SolvedDependency:
	values: Dict[str, Any]
	errors: List[Any]
	response: WerkzeugResponse
