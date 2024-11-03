import inspect
import os


def extract_endpoint_relative_path(func):
	"""
	Extract the relative path of the endpoint from the function for the API docs.
	"""
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
