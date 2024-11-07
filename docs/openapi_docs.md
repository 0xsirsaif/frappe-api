# Setting Up OpenAPI Documentation in Frappe

This guide explains how to set up automatic OpenAPI documentation using Swagger UI in your Frappe application.

## 1. Create Portal Page Directory

```bash
mkdir -p templates/pages/docs/
```

`/docs` is the directory where the Swagger UI will be served from `http://{site}.com/docs`. You can change this to any directory you want.

## 2. Create `index.html` inside the `docs` directory, add the following code:

```html
{% extends "templates/web.html" %}

{% block title %} Frappe API {% endblock %}

{%- block header -%}
<meta charset="UTF-8">
  <title>Frappe API</title>
  <link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700|Source+Code+Pro:300,600|Titillium+Web:400,600,700" rel="stylesheet">
  <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.9.4/swagger-ui.css" >
  <style>
    html
    {
      box-sizing: border-box;
      overflow: -moz-scrollbars-vertical;
      overflow-y: scroll;
    }
    *,
    *:before,
    *:after
    {
      box-sizing: inherit;
    }
    body {
      margin:0;
      background: #fafafa;
    }
  </style>
{% endblock %}


{%- block page_content -%}
<div id="swagger-ui"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.9.4/swagger-ui-bundle.js"> </script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.9.4/swagger-ui-standalone-preset.js"> </script>
<script>
  var spec = JSON.parse('{{ data | tojson | safe }}');
  const ui = SwaggerUIBundle({
    spec: spec,
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl
    ],
    layout: "StandaloneLayout",
    requestInterceptor: (request) => {
      request.headers['X-Frappe-CSRF-Token'] = frappe.csrf_token;
      return request;
    }
  })
</script>
{% endblock %}

```

## 3. Create `index.py` inside the `docs` directory, with the following code:

```python
# import your FrappeAPI app
from your_app.apis import app

# openapi() is a method that returns the auto-generated OpenAPI schema
# You could add more context to the ctx object to pass additional data to the template
# For example, you could add a "title" or "description" to the API docs
def get_context(ctx):
    ctx.data = app.openapi()
```

## 4. Access Documentation

After setting up the files:

1. Restart your Frappe server
2. Access your documentation at: `http://your-site/docs`

## Notes

- The documentation will automatically update when you modify your API endpoints
- The CSRF token is automatically included in API requests through the request interceptor
