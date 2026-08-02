import json
def inject(event, text):
    """Print model-only context, hidden from the user's transcript. Caller must exit 0."""
    if not text:
        return
    print(json.dumps({"suppressOutput": True, "hookSpecificOutput": {"hookEventName": event, "additionalContext": text[:10000]}}))
