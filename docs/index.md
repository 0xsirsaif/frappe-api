# FrappeAPI

Better APIs for Frappe!

⚠️ **Alert: Beta Version**
This project is currently in beta. Expect changes and improvements as we work towards a stable release.

## Why?

The goal is to build a better API framework for Frappe.

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
