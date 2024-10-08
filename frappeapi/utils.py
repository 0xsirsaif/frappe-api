import inspect
import os
from typing import Any


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
