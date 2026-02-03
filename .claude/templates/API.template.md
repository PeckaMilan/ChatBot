# {{PROJECT_NAME}} - API Documentation

> Version: {{API_VERSION}}
> Base URL: `{{BASE_URL}}`
> Last Updated: {{LAST_UPDATED}}

## Overview

{{API_OVERVIEW_DESCRIPTION}}

### Authentication

{{AUTH_METHOD_DESCRIPTION}}

```{{LANGUAGE}}
{{AUTH_EXAMPLE}}
```

### Rate Limiting

| Tier | Requests/Minute | Requests/Day |
|------|-----------------|--------------|
| {{TIER_1}} | {{TIER_1_RPM}} | {{TIER_1_RPD}} |
| {{TIER_2}} | {{TIER_2_RPM}} | {{TIER_2_RPD}} |

### Response Format

All responses follow this structure:

```json
{
  "success": true,
  "data": { },
  "error": null,
  "meta": {
    "timestamp": "{{TIMESTAMP_FORMAT}}",
    "version": "{{API_VERSION}}"
  }
}
```

---

## Endpoints / Functions

### {{CATEGORY_1}}

#### {{ENDPOINT_1_NAME}}

{{ENDPOINT_1_DESCRIPTION}}

**Endpoint:** `{{HTTP_METHOD}} {{ENDPOINT_1_PATH}}`

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `{{PARAM_1}}` | {{PARAM_1_TYPE}} | {{PARAM_1_REQUIRED}} | {{PARAM_1_DEFAULT}} | {{PARAM_1_DESC}} |
| `{{PARAM_2}}` | {{PARAM_2_TYPE}} | {{PARAM_2_REQUIRED}} | {{PARAM_2_DEFAULT}} | {{PARAM_2_DESC}} |

**Request Example:**

```{{LANGUAGE}}
{{ENDPOINT_1_REQUEST_EXAMPLE}}
```

**Response Example:**

```json
{{ENDPOINT_1_RESPONSE_EXAMPLE}}
```

---

#### {{ENDPOINT_2_NAME}}

{{ENDPOINT_2_DESCRIPTION}}

**Endpoint:** `{{HTTP_METHOD}} {{ENDPOINT_2_PATH}}`

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `{{PARAM_1}}` | {{PARAM_1_TYPE}} | {{PARAM_1_REQUIRED}} | {{PARAM_1_DEFAULT}} | {{PARAM_1_DESC}} |

**Request Example:**

```{{LANGUAGE}}
{{ENDPOINT_2_REQUEST_EXAMPLE}}
```

**Response Example:**

```json
{{ENDPOINT_2_RESPONSE_EXAMPLE}}
```

---

### {{CATEGORY_2}}

#### {{ENDPOINT_3_NAME}}

{{ENDPOINT_3_DESCRIPTION}}

**Endpoint:** `{{HTTP_METHOD}} {{ENDPOINT_3_PATH}}`

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `{{PARAM_1}}` | {{PARAM_1_TYPE}} | {{PARAM_1_REQUIRED}} | {{PARAM_1_DEFAULT}} | {{PARAM_1_DESC}} |

**Request Example:**

```{{LANGUAGE}}
{{ENDPOINT_3_REQUEST_EXAMPLE}}
```

**Response Example:**

```json
{{ENDPOINT_3_RESPONSE_EXAMPLE}}
```

---

<!-- Add more endpoints as needed -->

## Function Reference

### {{FUNCTION_1_NAME}}

{{FUNCTION_1_DESCRIPTION}}

**Signature:**

```{{LANGUAGE}}
{{FUNCTION_1_SIGNATURE}}
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `{{PARAM_1}}` | {{PARAM_1_TYPE}} | {{PARAM_1_REQUIRED}} | {{PARAM_1_DEFAULT}} | {{PARAM_1_DESC}} |
| `{{PARAM_2}}` | {{PARAM_2_TYPE}} | {{PARAM_2_REQUIRED}} | {{PARAM_2_DEFAULT}} | {{PARAM_2_DESC}} |

**Returns:**

| Type | Description |
|------|-------------|
| {{RETURN_TYPE}} | {{RETURN_DESC}} |

**Example:**

```{{LANGUAGE}}
{{FUNCTION_1_EXAMPLE}}
```

---

### {{FUNCTION_2_NAME}}

{{FUNCTION_2_DESCRIPTION}}

**Signature:**

```{{LANGUAGE}}
{{FUNCTION_2_SIGNATURE}}
```

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `{{PARAM_1}}` | {{PARAM_1_TYPE}} | {{PARAM_1_REQUIRED}} | {{PARAM_1_DEFAULT}} | {{PARAM_1_DESC}} |

**Returns:**

| Type | Description |
|------|-------------|
| {{RETURN_TYPE}} | {{RETURN_DESC}} |

**Example:**

```{{LANGUAGE}}
{{FUNCTION_2_EXAMPLE}}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "{{ERROR_CODE}}",
    "message": "{{ERROR_MESSAGE}}",
    "details": { }
  }
}
```

### Error Codes

| Code | HTTP Status | Description | Resolution |
|------|-------------|-------------|------------|
| `{{ERROR_1_CODE}}` | {{ERROR_1_STATUS}} | {{ERROR_1_DESC}} | {{ERROR_1_RESOLUTION}} |
| `{{ERROR_2_CODE}}` | {{ERROR_2_STATUS}} | {{ERROR_2_DESC}} | {{ERROR_2_RESOLUTION}} |
| `{{ERROR_3_CODE}}` | {{ERROR_3_STATUS}} | {{ERROR_3_DESC}} | {{ERROR_3_RESOLUTION}} |
| `{{ERROR_4_CODE}}` | {{ERROR_4_STATUS}} | {{ERROR_4_DESC}} | {{ERROR_4_RESOLUTION}} |

### Common HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource does not exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

### Error Handling Best Practices

1. **Always check `success` field** before processing response
2. **Implement retry logic** for 5xx errors with exponential backoff
3. **Handle rate limiting** by respecting `Retry-After` header
4. **Log error details** including `error.code` for debugging

**Example Error Handling:**

```{{LANGUAGE}}
{{ERROR_HANDLING_EXAMPLE}}
```

---

## Webhooks

### {{WEBHOOK_1_NAME}}

**Event:** `{{WEBHOOK_1_EVENT}}`

**Payload:**

```json
{{WEBHOOK_1_PAYLOAD}}
```

**Verification:**

```{{LANGUAGE}}
{{WEBHOOK_VERIFICATION_EXAMPLE}}
```

---

## SDK / Client Libraries

| Language | Package | Installation |
|----------|---------|--------------|
| {{LANG_1}} | {{PACKAGE_1}} | `{{INSTALL_1}}` |
| {{LANG_2}} | {{PACKAGE_2}} | `{{INSTALL_2}}` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| {{VERSION_1}} | {{DATE_1}} | {{CHANGES_1}} |
| {{VERSION_2}} | {{DATE_2}} | {{CHANGES_2}} |

---

**Need Help?** Contact {{SUPPORT_CONTACT}}
