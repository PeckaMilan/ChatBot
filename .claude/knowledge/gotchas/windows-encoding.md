# Windows-1250 Encoding on Czech Sites

**Category:** gotcha
**Created:** 2025-02-03
**Confidence:** high
**Source:** discovered (SuperAI/dash, SuperAI/legi)

## Problem
Czech government websites return content in Windows-1250 encoding, not UTF-8. Parsing without proper decoding results in garbled Czech characters (ěščřžýáíé).

## Symptoms
- Garbled text: `Ä›Ã¡Â` instead of `čář`
- UnicodeDecodeError in Python
- Broken diacritics in scraped content

## Affected Sites
- PSP.cz (Parliament)
- vlada.gov.cz (Government)
- Most Czech government portals

## Solution

### JavaScript/Node.js
```javascript
const decoder = new TextDecoder('windows-1250');
const text = decoder.decode(buffer);
```

### Python
```python
response = requests.get(url)
response.encoding = 'windows-1250'
text = response.text
```

### Fetch API
```javascript
const response = await fetch(url);
const buffer = await response.arrayBuffer();
const decoder = new TextDecoder('windows-1250');
const text = decoder.decode(buffer);
```

## Prevention
Always check `Content-Type` header for charset. If not specified and site is Czech government, assume Windows-1250.

## Related
- [PSP.cz API](../apis/psp-cz.md)
