import os


DEFAULT_API_HOST = "127.0.0.1"
LAB_BLOCKED_ENDPOINTS = frozenset({
    "/api/command",
    "/api/payloads/generate",
    "/api/v2/evolution/execute",
})


def lab_profile_enabled():
    return os.environ.get("AETHEROPS_LAB") == "1"


def is_lab_blocked_path(path):
    return lab_profile_enabled() and path in LAB_BLOCKED_ENDPOINTS
