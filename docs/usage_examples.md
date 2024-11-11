# Usage Examples

> **Note**: FrappeAPI follows FastAPI's interface and semantics. For in-depth information about specific features, you can refer to [FastAPI's documentation](https://fastapi.tiangolo.com/).

## Query Parameters

FrappeAPI provides rich support for query parameters with automatic validation and documentation. Here are examples of different query parameter features:

### 1. Automatic Type Parsing

Query parameters are automatically parsed based on type hints:

```python
@app.get()
def get_product_details(
    product_id: int,
    unit_price: float,
    in_stock: bool
):
    return {
        "product_id": product_id,  # "123" -> 123
        "unit_price": unit_price,  # "9.99" -> 9.99
        "in_stock": in_stock      # "true" -> True
    }
# GET https://example.com/api/method/my_app.api.v1.get_product_details?product_id=123&unit_price=9.99&in_stock=true
# Response: {"product_id": 123, "unit_price": 9.99, "in_stock": true}
```

### 2. Required Parameters

You can specify required parameters in different ways:

```python
@app.get()
def get_user_profile(
    user_id: str,           # Required by default
    include_photo: str = ... # Required using Ellipsis
):
    return {
        "user_id": user_id,
        "include_photo": include_photo
    }
# GET https://example.com/api/method/my_app.api.v1.get_user_profile?user_id=USR001&include_photo=true
# Response: {"user_id": "USR001", "include_photo": "true"}
```

### 3. Optional Parameters

Optional parameters can have default values or be nullable:

```python
@app.get()
def list_products(
    category: str = "all",        # Optional with default
    page: int = 1,                # Optional with default
    search: str | None = None     # Optional without default
):
    return {
        "category": category,
        "page": page,
        "search": search
    }
# GET https://example.com/api/method/my_app.api.v1.list_products?category=electronics&page=2&search=laptop
# Response: {"category": "electronics", "page": 2, "search": "laptop"}
# GET https://example.com/api/method/my_app.api.v1.list_products
# Response: {"category": "all", "page": 1, "search": null}
```

### 4. Enum Parameters

Use enums for parameters with predefined values:

```python
from enum import Enum

class OrderStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    cancelled = "cancelled"

@app.get()
def list_orders(
    status: OrderStatus = OrderStatus.pending,  # Enum with default
    sort_by: Literal["date", "status"] = "date" # Literal for fixed values
):
    return {
        "status": status,
        "sort_by": sort_by
    }
# GET https://example.com/api/method/my_app.api.v1.list_orders?status=processing&sort_by=status
# Response: {"status": "processing", "sort_by": "status"}
# GET https://example.com/api/method/my_app.api.v1.list_orders
# Response: {"status": "pending", "sort_by": "date"}
```

### 5. Boolean Parameters

Boolean parameters support multiple formats:

```python
@app.get()
def filter_items(
    in_stock: bool = True,     # Accepts: true/1/yes/on
    is_featured: bool = False  # Accepts: false/0/no/off
):
    return {
        "in_stock": in_stock,       # "yes" -> True
        "is_featured": is_featured  # "0" -> False
    }
# GET https://example.com/api/method/my_app.api.v1.filter_items?in_stock=yes&is_featured=0
# Response: {"in_stock": true, "is_featured": false}
# GET https://example.com/api/method/my_app.api.v1.filter_items?in_stock=1&is_featured=no
# Response: {"in_stock": true, "is_featured": false}
```

### 6. List Parameters

Handle parameters that can appear multiple times in the URL:

```python
@app.get()
def search_products(
    tags: List[str] = Query(default=[]),      # Multiple string values
    categories: List[int] = Query(default=[])  # Multiple integer values
):
    return {
        "tags": tags,           
        "categories": categories 
    }
# GET https://example.com/api/method/my_app.api.v1.search_products?tags=electronics&tags=sale&categories=1&categories=2
# Response: {"tags": ["electronics", "sale"], "categories": [1, 2]}
```

### 7. Aliased Parameters

Use different parameter names in the URL:

```python
@app.get()
def search_items(
    search_text: Annotated[str, Query(alias="q")] = "",     # Use as ?q=value
    page_number: Annotated[int, Query(alias="p")] = 1,      # Use as ?p=2
    items_per_page: Annotated[int, Query(alias="size")] = 10 # Use as ?size=20
):
    return {
        "search": search_text,
        "page": page_number,
        "per_page": items_per_page
    }
# GET https://example.com/api/method/my_app.api.v1.search_items?q=laptop&p=2&size=20
# Response: {"search": "laptop", "page": 2, "per_page": 20}
```

### 8. Query Parameter Models

Group related parameters using Pydantic models:

```python
from pydantic import BaseModel, Field
from typing import List

class ProductFilter(BaseModel):
    search: str | None = None
    category: str = "all"
    min_price: float = Field(0, ge=0)
    max_price: float | None = None
    tags: List[str] = []
    in_stock: bool = True
    sort_by: Literal["price", "name", "date"] = "date"

@app.get()
def filter_products(
    filters: Annotated[ProductFilter, Query()]
):
    return filters
# GET https://example.com/api/method/my_app.api.v1.filter_products?search=laptop&category=electronics&min_price=100&tags=new&tags=sale
# Response: {
#     "search": "laptop",
#     "category": "electronics",
#     "min_price": 100.0,
#     "max_price": null,
#     "tags": ["new", "sale"],
#     "in_stock": true,
#     "sort_by": "date"
# }
```

### 9. Documented Parameters

Add metadata for automatic documentation generation:

```python
@app.get()
def search_catalog(
    q: Annotated[
        str, 
        Query(
            title="Search Query",
            description="Text to search for in product catalog",
            min_length=2,
            max_length=50,
            example="laptop"
        )
    ] = "",
    category: Annotated[
        str,
        Query(
            title="Category Filter",
            description="Filter results by product category",
            example="electronics"
        )
    ] = "all"
):
    return {"query": q, "category": category}
# GET https://example.com/api/method/my_app.api.v1.search_catalog?q=laptop&category=electronics
# Response: {"query": "laptop", "category": "electronics"}
```

## Request Body Parameters

FrappeAPI supports various ways to handle request body data. Here are examples of different body parameter features:

### 1. Single Model Body

Use Pydantic models to validate request body:

```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    price: float = Field(..., gt=0)
    tax: float | None = None

@app.post()
def create_item(item: Item):
    return item
# POST https://example.com/api/method/my_app.api.v1.create_item
# Request Body:
# {
#     "name": "Laptop",
#     "description": "High-performance laptop",
#     "price": 999.99,
#     "tax": 79.99
# }
# Response: Same as request body
```

### 2. Multiple Body Parameters

Handle multiple body parameters:

```python
class User(BaseModel):
    username: str
    email: str

class Item(BaseModel):
    name: str
    price: float

@app.post()
def create_user_item(
    user: User,
    item: Item
):
    return {"user": user, "item": item}
# POST https://example.com/api/method/my_app.api.v1.create_user_item
# Request Body:
# {
#     "user": {
#         "username": "john_doe",
#         "email": "john@example.com"
#     },
#     "item": {
#         "name": "Laptop",
#         "price": 999.99
#     }
# }
# Response: Same as request body
```

### 3. Nested Models

Use nested Pydantic models for complex data:

```python
class Image(BaseModel):
    url: HttpUrl
    name: str

class Product(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None
    tags: List[str] = []
    images: List[Image]

@app.post()
def create_product(product: Product):
    return product
# POST https://example.com/api/method/my_app.api.v1.create_product
# Request Body:
# {
#     "name": "Awesome Laptop",
#     "description": "Best laptop ever",
#     "price": 999.99,
#     "tags": ["electronics", "computers"],
#     "images": [
#         {
#             "url": "https://example.com/img1.jpg",
#             "name": "Front View"
#         },
#         {
#             "url": "https://example.com/img2.jpg",
#             "name": "Side View"
#         }
#     ]
# }
# Response: Same as request body
```

### 4. Body with Extra Fields

Control how extra fields are handled:

```python
class StrictItem(BaseModel):
    model_config = {"extra": "forbid"}  # Will reject extra fields
    name: str
    price: float

class FlexibleItem(BaseModel):
    model_config = {"extra": "allow"}   # Will allow extra fields
    name: str
    price: float

@app.post()
def create_items(
    strict: StrictItem,
    flexible: FlexibleItem
):
    return {"strict": strict, "flexible": flexible}
# POST https://example.com/api/method/my_app.api.v1.create_items
# Request Body:
# {
#     "strict": {
#         "name": "Laptop",
#         "price": 999.99
#         # Extra fields here would cause validation error
#     },
#     "flexible": {
#         "name": "Mouse",
#         "price": 49.99,
#         "color": "black",  # Extra field allowed
#         "in_stock": true   # Extra field allowed
#     }
# }
```

### 5. Body with Field Validation

Add validation rules to fields:

```python
class Product(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Product name"
    )
    price: float = Field(
        ...,
        gt=0,
        le=1000000,
        description="Product price in USD"
    )
    sku: str = Field(
        ...,
        pattern="^[A-Z]{2}-[0-9]{4}$",
        description="Stock keeping unit (e.g., AB-1234)"
    )
    tags: List[str] = Field(
        default=[],
        max_items=5,
        description="Product tags"
    )

@app.post()
def create_product(product: Product):
    return product
# POST https://example.com/api/method/my_app.api.v1.create_product
# Request Body:
# {
#     "name": "Gaming Laptop",
#     "price": 1299.99,
#     "sku": "LP-1234",
#     "tags": ["electronics", "gaming"]
# }
```

### 6. Body with Computed Fields

Include computed fields in your models:

```python
class Order(BaseModel):
    items: List[str]
    unit_price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    
    @property
    def total_price(self) -> float:
        return self.unit_price * self.quantity
    
    @property
    def item_count(self) -> int:
        return len(self.items)

@app.post()
def create_order(order: Order):
    return {
        **order.model_dump(),
        "total_price": order.total_price,
        "item_count": order.item_count
    }
# POST https://example.com/api/method/my_app.api.v1.create_order
# Request Body:
# {
#     "items": ["laptop", "mouse", "keyboard"],
#     "unit_price": 999.99,
#     "quantity": 2
# }
# Response:
# {
#     "items": ["laptop", "mouse", "keyboard"],
#     "unit_price": 999.99,
#     "quantity": 2,
#     "total_price": 1999.98,
#     "item_count": 3
# }
```

### 7. Form Data

Handle form data submissions:

```python
from fastapi import Form

@app.post()
def create_user_profile(
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    bio: Annotated[str | None, Form()] = None
):
    return {
        "username": username,
        "email": email,
        "bio": bio
    }
# POST https://example.com/api/method/my_app.api.v1.create_user_profile
# Content-Type: application/x-www-form-urlencoded
# Form Data:
#   username=johndoe
#   email=john@example.com
#   password=secretpass
#   bio=Hello World
```

## File Uploads

FrappeAPI provides two approaches for handling file uploads, optimized for different use cases:

### 1. Small Files (In-Memory)

For small files, use `File()` which loads the entire file into memory:

```python
from typing import Annotated
from frappeapi import File, Form

@app.post()
def upload_document(
    file: Annotated[bytes, File()],
    description: Annotated[str | None, Form()] = None
):
    content = len(file)  # File content is available as bytes
    return {
        "file_size": content,
        "description": description
    }
# POST https://example.com/api/method/my_app.api.v1.upload_document
# Content-Type: multipart/form-data
# Form Data:
#   file=@small_doc.pdf
#   description=Small document
```

### 2. Large Files (Streamed)

For large files, use `UploadFile` which streams the file and provides more metadata:

```python
from frappeapi import UploadFile

@app.post()
def upload_large_file(
    file: UploadFile,
    chunk_size: Annotated[int, Form()] = 8192
):
    # Access file metadata
    file_info = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": 0
    }
    
    # Access the raw Python file object for non-async operations
    while chunk := file.file.read(chunk_size):
        file_info["size"] += len(chunk)
        # Process chunk here...
    
    return file_info
# POST https://example.com/api/method/my_app.api.v1.upload_large_file
# Content-Type: multipart/form-data
# Form Data:
#   file=@large_video.mp4
#   chunk_size=8192
```

Note: Optional file uploads, multiple file uploads, and multiple `UploadFile` fields are not yet supported.

## Response Models and Return Types

FrappeAPI provides several ways to define and control response data. Response models can be defined using return type annotations or the `response_model` parameter (which takes priority if both are used). Response models automatically filter and validate the returned data to match the defined schema.

### 1. Basic Response Model

Use Pydantic models to define response structure:

```python
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True

@app.get(response_model=UserResponse)  # Will filter response to match UserResponse
def get_user(user_id: int) -> UserResponse:  # Return type provides IDE support
    return {
        "id": user_id,
        "username": "john_doe",
        "email": "john@example.com",
        "is_active": True,
        "password": "secret",  # Will be filtered out from response
        "role": "admin"       # Will be filtered out from response
    }
# GET https://example.com/api/method/my_app.api.v1.get_user?user_id=123
# Response: {
#     "id": 123,
#     "username": "john_doe",
#     "email": "john@example.com",
#     "is_active": true
# }
```

### 2. List Response Model

Handle list responses with type validation:

```python
class Product(BaseModel):
    id: int
    name: str
    price: float

@app.get(response_model=List[Product])
def list_products(category: str = "all"):
    return [
        {"id": 1, "name": "Laptop", "price": 999.99},
        {"id": 2, "name": "Mouse", "price": 24.99},
        {"id": 3, "name": "Keyboard", "price": 49.99}
    ]
# GET https://example.com/api/method/my_app.api.v1.list_products?category=all
# Response: [
#     {"id": 1, "name": "Laptop", "price": 999.99},
#     {"id": 2, "name": "Mouse", "price": 24.99},
#     {"id": 3, "name": "Keyboard", "price": 49.99}
# ]
```

## Error Handling

FrappeAPI provides built-in exception handlers and allows you to customize error handling.

### 1. Built-in Exception Handlers

FrappeAPI includes default handlers for common exceptions:

```python
from frappeapi.exceptions import HTTPException, RequestValidationError, ResponseValidationError

@app.get()
def get_item(item_id: int):
    if item_id < 0:
        raise HTTPException(status_code=400, detail="Item ID must be positive")
    if item_id > 1000:
        raise HTTPException(
            status_code=400, 
            detail="Item ID too large",
            headers={"X-Error": "INVALID_ID"}
        )
    return {"id": item_id}
# GET https://example.com/api/method/my_app.api.v1.get_item?item_id=-1
# Response (400): {
#     "detail": "Item ID must be positive"
# }
```

### 2. Custom Exception Handlers

You can add handlers for your own exceptions:

```python
class ItemNotFound(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

@app.exception_handler(ItemNotFound)
def item_not_found_handler(request: Request, exc: ItemNotFound):
    return JSONResponse(
        status_code=404,
        content={
            "error": "ITEM_NOT_FOUND",
            "detail": f"Item {exc.item_id} not found",
        }
    )

@app.get()
def get_item(item_id: int):
    if item_id == 404:
        raise ItemNotFound(item_id)
    return {"id": item_id}
# GET https://example.com/api/method/my_app.api.v1.get_item?item_id=404
# Response (404): {
#     "error": "ITEM_NOT_FOUND",
#     "detail": "Item 404 not found"
# }
```

### 3. Override Default Handlers

You can override the default exception handlers:

```python
@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "details": [
                {
                    "field": e["loc"][-1],
                    "message": e["msg"]
                }
                for e in exc.errors()
            ]
        }
    )

@app.post()
def create_item(item: Item):
    return item
# POST https://example.com/api/method/my_app.api.v1.create_item
# Request Body: {"price": "invalid"}
# Response (422): {
#     "error": "VALIDATION_ERROR",
#     "details": [
#         {
#             "field": "price",
#             "message": "value is not a valid float"
#         }
#     ]
# }
```

## Field Validation and Metadata

FrappeAPI supports various field validations and metadata annotations:

### 1. String Validations

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9-_ ]+$",  # Only alphanumeric, space, hyphen and underscore
        description="Product name (3-50 chars, alphanumeric)"
    )
    sku: str = Field(
        pattern="^[A-Z]{2}-[0-9]{4}$",  # Format: XX-0000
        description="Stock keeping unit (e.g., AB-1234)"
    )

@app.post()
def create_product(product: Product):
    return product
# POST https://example.com/api/method/my_app.api.v1.create_product
# Request Body: {"name": "A", "sku": "invalid"}
# Response (422): {
#     "detail": [
#         {
#             "type": "string_too_short",
#             "loc": ["body", "name"],
#             "msg": "String should have at least 3 characters"
#         },
#         {
#             "type": "string_pattern_mismatch",
#             "loc": ["body", "sku"],
#             "msg": "String should match pattern '^[A-Z]{2}-[0-9]{4}$'"
#         }
#     ]
# }
```

### 2. Numeric Validations

```python
class Order(BaseModel):
    quantity: int = Field(gt=0, le=100, description="Order quantity (1-100)")
    unit_price: float = Field(gt=0, le=1000000, description="Price in USD")
    discount_percent: float = Field(ge=0, le=100, description="Discount percentage")

@app.post()
def create_order(order: Order):
    return order
# POST https://example.com/api/method/my_app.api.v1.create_order
# Request Body: {"quantity": 0, "unit_price": -10, "discount_percent": 101}
# Response (422): {
#     "detail": [
#         {
#             "type": "greater_than",
#             "loc": ["body", "quantity"],
#             "msg": "Input should be greater than 0"
#         },
#         {
#             "type": "greater_than",
#             "loc": ["body", "unit_price"],
#             "msg": "Input should be greater than 0"
#         },
#         {
#             "type": "less_than_equal",
#             "loc": ["body", "discount_percent"],
#             "msg": "Input should be less than or equal to 100"
#         }
#     ]
# }
```

### 3. API Metadata

Add metadata to your API endpoints:

```python
from typing import Annotated
from frappeapi import Query

@app.get(
    description="Retrieve product details by ID",
    summary="Get Product",
    include_in_schema=True,
    tags=["Products"]
)
def get_product(
    product_id: Annotated[int, Query(
        title="Product ID",
        description="Unique identifier for the product",
        gt=0
    )]
):
    return {"id": product_id}
# This metadata will be visible in the API documentation at /docs
```

## Header Parameters

FrappeAPI supports header parameters in your API endpoints. Header parameters are automatically converted from hyphen to underscore:

```python
from typing import Annotated
from frappeapi import Header

@app.get()
def get_user_info(
    user_agent: Annotated[str, Header()],      # Will read from User-Agent
    x_custom_header: Annotated[str, Header()]  # Will read from X-Custom-Header
):
    return {
        "user_agent": user_agent,
        "custom_header": x_custom_header
    }
# GET https://example.com/api/method/my_app.api.v1.get_user_info
# Headers:
#   User-Agent: Mozilla/5.0
#   X-Custom-Header: custom-value
# Response: {
#     "user_agent": "Mozilla/5.0",
#     "custom_header": "custom-value"
# }
```

Note: Currently, header parameters as Pydantic models, duplicate headers, and forbidding extra headers are not supported.
