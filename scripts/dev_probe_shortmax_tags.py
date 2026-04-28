"""探查 ShortMax 标签和详情字段"""
import json
from base64 import b64decode, b64encode

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

KEY = b"shortwebapiaesen"
BASE = "https://shortweb.shorttv.live/app-api/app"
HEADERS = {
    "Content-Type": "application/json",
    "X-Encrypted": "true",
    "Language-Code": "en",
}


def enc(payload):
    cipher = AES.new(KEY, AES.MODE_CBC, iv=KEY)
    return b64encode(
        cipher.encrypt(
            pad(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 16)
        )
    )


def dec(text):
    cipher = AES.new(KEY, AES.MODE_CBC, iv=KEY)
    return json.loads(unpad(cipher.decrypt(b64decode(text.strip())), 16).decode("utf-8"))


def post(path, payload):
    r = httpx.post(f"{BASE}{path}", headers=HEADERS, content=enc(payload), timeout=30)
    r.raise_for_status()
    return dec(r.text)


print("--- cmsLabelNew/queryList sample ---")
labels = post("/cmsLabelNew/queryList", {})
print(json.dumps(labels, ensure_ascii=False)[:2000])

print("--- cmsClassNew/queryList sample ---")
classes = post("/cmsClassNew/queryList", {})
print(json.dumps(classes, ensure_ascii=False)[:2000])

print("--- queryDetail of shortPlayId=20071 ---")
detail = post("/cmsShortPlay/queryDetail", {"shortPlayId": 20071})
print(json.dumps(detail, ensure_ascii=False)[:3000])

print("--- queryPage labelId sample ---")
if isinstance(labels, dict) and labels.get("data"):
    labs = labels.get("data") or []
    if labs:
        first_label = labs[0]
        print("first label:", first_label)
        page = post(
            "/cmsShortPlay/queryPage",
            {
                "pageNo": 1,
                "pageSize": 5,
                "labelId": first_label.get("labelId"),
                "classId": "",
            },
        )
        print(json.dumps(page, ensure_ascii=False)[:1500])
