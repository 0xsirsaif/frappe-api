# FrappeAPI

Build APIs for Frappe with the simplicity of FastAPI!

⚠️ **Alert: Beta Version**

This project is currently in beta and not yet ready for production use. Expect changes and improvements as we work towards a stable release.

## Installation

```bash
pip install frappeapi
```

## Example

Here's an example of how to use FrappeAPI:

```python
from frappeapi import FrappeAPI

app = FrappeAPI()

@app.get()
def get_book(isbn: str):
    book = {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "isbn": "9780446310789",
        "available": True
    }
    return book
```
