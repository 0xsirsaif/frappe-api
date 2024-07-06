from typing import Dict, List, Tuple, Union
from urllib.parse import parse_qsl, urlencode


class QueryParams:
	"""
	An immutable dictionary-like structure for managing query parameters.
	"""

	def __init__(
		self, value: Union[str, bytes, List[Tuple[str, str]], Dict[str, str], None] = None, **kwargs: str
	) -> None:
		# Temporary storage for initializing
		initial_data: Dict[str, str] = {}

		if isinstance(value, str):
			initial_data.update(parse_qsl(value, keep_blank_values=True))
		elif isinstance(value, bytes):
			initial_data.update(parse_qsl(value.decode("utf-8"), keep_blank_values=True))
		elif isinstance(value, (list, dict)):
			initial_data.update(value)

		# Update with any additional keyword arguments
		initial_data.update(kwargs)

		# Convert all keys and values to strings
		self._data = {str(k): str(v) for k, v in initial_data.items()}

	def to_dict(self) -> Dict[str, str]:
		"""
		Convert the QueryParams to a dictionary.
		Provides a safe way to interact with the parameters without modifying them.
		"""
		return self._data.copy()

	def __getitem__(self, key: str) -> str:
		return self._data[key]

	def __iter__(self):
		return iter(self._data)

	def items(self):
		return self._data.items()

	def keys(self):
		return self._data.keys()

	def values(self):
		return self._data.values()

	def __str__(self) -> str:
		return urlencode(self._data)

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self._data!r})"

	def __len__(self) -> int:
		return len(self._data)

	def get(self, key: str, default: Union[str, None] = None) -> Union[str, None]:
		return self._data.get(key, default)
