from __future__ import annotations

import typing
from urllib.parse import parse_qsl, urlencode

_KeyType = typing.TypeVar("_KeyType")
# Mapping keys are invariant but their values are covariant since
# you can only read them
# that is, you can't do `Mapping[str, Animal]()["fido"] = Dog()`
_CovariantValueType = typing.TypeVar("_CovariantValueType", covariant=True)


class ImmutableMultiDict(typing.Mapping[_KeyType, _CovariantValueType]):
	_dict: dict[_KeyType, _CovariantValueType]

	def __init__(
		self,
		*args: ImmutableMultiDict[_KeyType, _CovariantValueType]
		| typing.Mapping[_KeyType, _CovariantValueType]
		| typing.Iterable[tuple[_KeyType, _CovariantValueType]],
		**kwargs: typing.Any,
	) -> None:
		assert len(args) < 2, "Too many arguments."

		value: typing.Any = args[0] if args else []
		if kwargs:
			value = ImmutableMultiDict(value).multi_items() + ImmutableMultiDict(kwargs).multi_items()

		if not value:
			_items: list[tuple[typing.Any, typing.Any]] = []
		elif hasattr(value, "multi_items"):
			value = typing.cast(ImmutableMultiDict[_KeyType, _CovariantValueType], value)
			_items = list(value.multi_items())
		elif hasattr(value, "items"):
			value = typing.cast(typing.Mapping[_KeyType, _CovariantValueType], value)
			_items = list(value.items())
		else:
			value = typing.cast("list[tuple[typing.Any, typing.Any]]", value)
			_items = list(value)

		self._dict = {k: v for k, v in _items}
		self._list = _items

	def getlist(self, key: typing.Any) -> list[_CovariantValueType]:
		return [item_value for item_key, item_value in self._list if item_key == key]

	def keys(self) -> typing.KeysView[_KeyType]:
		return self._dict.keys()

	def values(self) -> typing.ValuesView[_CovariantValueType]:
		return self._dict.values()

	def items(self) -> typing.ItemsView[_KeyType, _CovariantValueType]:
		return self._dict.items()

	def multi_items(self) -> list[tuple[_KeyType, _CovariantValueType]]:
		return list(self._list)

	def __getitem__(self, key: _KeyType) -> _CovariantValueType:
		return self._dict[key]

	def __contains__(self, key: typing.Any) -> bool:
		return key in self._dict

	def __iter__(self) -> typing.Iterator[_KeyType]:
		return iter(self.keys())

	def __len__(self) -> int:
		return len(self._dict)

	def __eq__(self, other: typing.Any) -> bool:
		if not isinstance(other, self.__class__):
			return False
		return sorted(self._list) == sorted(other._list)

	def __repr__(self) -> str:
		class_name = self.__class__.__name__
		items = self.multi_items()
		return f"{class_name}({items!r})"


class QueryParams(ImmutableMultiDict[str, str]):
	"""
	An immutable multidict.
	"""

	def __init__(
		self,
		*args: ImmutableMultiDict[typing.Any, typing.Any]
		| typing.Mapping[typing.Any, typing.Any]
		| list[tuple[typing.Any, typing.Any]]
		| str
		| bytes,
		**kwargs: typing.Any,
	) -> None:
		assert len(args) < 2, "Too many arguments."

		value = args[0] if args else []

		if isinstance(value, str):
			super().__init__(parse_qsl(value, keep_blank_values=True), **kwargs)
		elif isinstance(value, bytes):
			super().__init__(parse_qsl(value.decode("latin-1"), keep_blank_values=True), **kwargs)
		else:
			super().__init__(*args, **kwargs)  # type: ignore[arg-type]
		self._list = [(str(k), str(v)) for k, v in self._list]
		self._dict = {str(k): str(v) for k, v in self._dict.items()}

	def __str__(self) -> str:
		return urlencode(self._list)

	def __repr__(self) -> str:
		class_name = self.__class__.__name__
		query_string = str(self)
		return f"{class_name}({query_string!r})"
