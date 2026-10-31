from security.signing import sign,verify

def test_independent_signing():
    secret='synthetic-independent-secret-'*2
    payload={'credential_id':'x','repository_commit_sha':'a'*40,'signature_algorithm':'HMAC-SHA256','verified_skills':['Python']}
    payload['signature']=sign(payload,secret)
    assert verify(dict(reversed(list(payload.items()))),secret)
    payload['repository_commit_sha']='b'*40
    assert not verify(payload,secret)

def test_wrong_secret():
    p={'signature_algorithm':'HMAC-SHA256'}
    p['signature']=sign(p,'a'*32)
    assert not verify(p,'b'*32)
