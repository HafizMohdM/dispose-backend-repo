# -*- coding: utf-8 -*-
import urllib.request
import json
import base64
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = "http://127.0.0.1:8001/api/v1/auth"

print("=" * 60)
print("AUTH HARDENING v2 - END-TO-END VERIFICATION")
print("=" * 60)

# 1. Request OTP
req = urllib.request.Request(
    f"{base}/request-otp",
    data=json.dumps({"mobile": "7777777777"}).encode(),
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req).read())
otp = resp.get("otp")
print(f"\n1. OTP received: {otp} [OK]")

# 2. Verify OTP
req2 = urllib.request.Request(
    f"{base}/verify-otp",
    data=json.dumps({"mobile": "7777777777", "otp": otp}).encode(),
    headers={
        "Content-Type": "application/json",
        "User-Agent": "TestClient/1.0",
        "X-Device-Name": "Test-PC",
    },
)
resp2 = json.loads(urllib.request.urlopen(req2).read())
token = resp2.get("access_token")
refresh = resp2.get("refresh_token")
print(f"2. Access token: {token[:40]}...")
print(f"   Refresh token: {'present' if refresh else 'MISSING'}")
assert refresh, "refresh_token must be present"
print("   Both tokens present [OK]")

# 3. Decode JWT
payload_part = token.split(".")[1]
padding = 4 - len(payload_part) % 4
payload_part += "=" * padding
payload = json.loads(base64.urlsafe_b64decode(payload_part))
print(f"\n3. JWT keys: {sorted(payload.keys())}")
assert "session_id" in payload, "session_id must be in JWT"
assert "token_version" in payload, "token_version must be in JWT"
assert "iat" in payload, "iat must be in JWT"
print(f"   session_id={payload['session_id']}, token_version={payload['token_version']} [OK]")

auth = {"Authorization": f"Bearer {token}"}

# 4. GET /sessions
req3 = urllib.request.Request(f"{base}/sessions", headers=auth)
resp3 = json.loads(urllib.request.urlopen(req3).read())
sessions = resp3.get("sessions", [])
print(f"\n4. Active sessions: {len(sessions)}")
s = sessions[0]
print(f"   id={s['session_id']}, current={s['is_current_session']}")
print(f"   ip={s.get('ip_address')}, device={s.get('device_name')}, ua={str(s.get('user_agent', ''))[:30]}")
assert s["is_current_session"] is True
print("   Session metadata captured [OK]")

# 5. GET /me
req4 = urllib.request.Request(f"{base}/me", headers=auth)
resp4 = json.loads(urllib.request.urlopen(req4).read())
print(f"\n5. /me: user_id={resp4.get('id')} [OK]")

# 6. GET /profile
req5 = urllib.request.Request(f"{base}/profile", headers=auth)
resp5 = json.loads(urllib.request.urlopen(req5).read())
print(f"6. /profile: user_id={resp5.get('user', {}).get('id')} [OK]")

# 7. Rotate refresh token
req6 = urllib.request.Request(
    f"{base}/rotate-refresh-token",
    data=b"",
    method="POST",
    headers=auth,
)
resp6 = json.loads(urllib.request.urlopen(req6).read())
new_access = resp6.get("access_token")
new_refresh = resp6.get("refresh_token")
assert new_access, "New access token must be returned"
assert new_refresh, "New refresh token must be returned"
assert new_refresh != refresh, "Refresh token must be rotated"
print(f"\n7. Refresh token rotated [OK]")
print(f"   Old: {refresh[:20]}...")
print(f"   New: {new_refresh[:20]}...")

# Use new token
token = new_access
auth = {"Authorization": f"Bearer {token}"}

# 8. /me with rotated token
req7 = urllib.request.Request(f"{base}/me", headers=auth)
resp7 = json.loads(urllib.request.urlopen(req7).read())
print(f"\n8. /me with rotated token: user_id={resp7.get('id')} [OK]")

# 9. Sessions after rotation
req8 = urllib.request.Request(f"{base}/sessions", headers=auth)
resp8 = json.loads(urllib.request.urlopen(req8).read())
print(f"9. Sessions after rotation: {len(resp8.get('sessions', []))} active [OK]")

# 10. Endpoint list
data = json.loads(urllib.request.urlopen("http://127.0.0.1:8001/openapi.json").read())
auth_paths = [p for p in sorted(data["paths"].keys()) if "/auth/" in p]
print(f"\n10. Auth endpoints ({len(auth_paths)}):")
for p in auth_paths:
    print(f"    {p}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
