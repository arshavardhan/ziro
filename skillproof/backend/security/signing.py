import hashlib
import hmac
import json

def canonical(payload):
    return json.dumps({k:v for k,v in payload.items() if k!='signature'},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def sign(payload,secret):
    if len(secret)<32:
        raise ValueError('Signing secret must contain at least 32 characters')
    return hmac.new(secret.encode(),canonical(payload),hashlib.sha256).hexdigest()

def verify(payload,secret):
    try:
        return payload.get('signature_algorithm')=='HMAC-SHA256' and hmac.compare_digest(sign(payload,secret),str(payload.get('signature','')))
    except (TypeError,ValueError,AttributeError):
        return False
