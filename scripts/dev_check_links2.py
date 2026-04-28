import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

links = {
    "dramabox":  "https://www.dramabox.com/drama/42000005228/Honey-Guess-Whos-the-REAL-BOSS",
    "flextv":    "https://www.flextv.cc/episodes/episode-1-tied-by-fate-XmzYE0Bz4g",
    "goodshort": "https://www.goodshort.com/dramas/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454",
    "melolo":    "https://melolo.com/dramas/fated-to-find-you",
    "moboreels": "https://www.moboreels.com/series/41896322",
    "netshort":  "https://netshort.com/episode/the-lions-captive-2044271853970653185",
    "reelshort": "https://www.reelshort.com/episodes/episode-1-the-alpha-s-dead-luna-k2bzfcqg5e",
    "shortmax":  "https://www.shorttv.live/drama/dubbedavery%E2%80%99s-gambit-20010",
    "serealplus": "https://www.sereal.plus",
}

with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=10) as client:
    for platform, url in links.items():
        try:
            r = client.get(url)
            print(f"[{platform:12}] {r.status_code}  {url[:80]}")
        except Exception as e:
            print(f"[{platform:12}] ERROR  {e}")
