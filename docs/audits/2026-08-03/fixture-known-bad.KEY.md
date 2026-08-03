# Known-bad fixture answer key

- Line 30: The cache-age condition is inverted: it reads and returns an expired entry while treating a fresh entry as a miss.
- Line 45: If `json.dump` or `os.replace` raises `OSError`, this return bypasses `handle.close()`, leaking the open temporary file.
- Line 60: `range(retries + 1)` makes one more HTTP request than the documented total-request limit.
- Line 67: `response.ensure_success()` is an invented `urllib` response API; standard responses do not provide this method.
- Line 69: The bare `except: pass` swallows errors from the actual HTTP request and parsing, hiding real failures.
- Line 78: Returning `{}` on exhaustion makes a fetch failure indistinguishable from a valid empty JSON object.
