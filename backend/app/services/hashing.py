import hashlib
import json

EXCLUDED_FIELDS = {"created_at", "updated_at", "hash"}

def canonical_hash(obj: dict) -> str:
    clean = {k: v for k, v in obj.items() if k not in EXCLUDED_FIELDS and v is not None}
    canonical = json.dumps(clean, sort_keys=True, separators=(',', ':'))
    return 'sha256:' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()