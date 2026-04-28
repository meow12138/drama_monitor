"""探查 Melolo 详情页标签结构"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://melolo.com"

# 抓两个不同的剧集详情页
test_urls = [
    "https://melolo.com/dramas/fated-to-find-you",
    "https://melolo.com/dramas/her-three-alphas",
]

for url in test_urls:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    r = httpx.get(url, headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. 找 genre/tag/category 相关链接
    print("\n--- Genre/Tag 链接 ---")
    for pat in ["/genre/", "/tag/", "/category/", "/genres/", "/tags/"]:
        links = soup.find_all("a", href=re.compile(pat))
        if links:
            print(f"  '{pat}': {[(a.get_text(strip=True), a.get('href')) for a in links[:5]]}")

    # 2. 在 RSC 流里找标签
    pushes = re.findall(r'self\.__next_f\.push\(\[(.*?)\]\)', html, re.DOTALL)
    combined = ""
    for push in pushes:
        m = re.match(r'\d+,(.+)', push.strip(), re.DOTALL)
        if m:
            content = m.group(1).strip()
            if content.startswith('"'):
                try:
                    combined += json.loads(content)
                except:
                    pass

    # 找 genre/tag/category 字段
    print("\n--- RSC 里的标签字段 ---")
    for kw in ["genre", "tag", "category", "label", "type", "subject"]:
        matches = re.findall(rf'"{kw}s?"\s*:\s*"([^"{{]+)"', combined, re.IGNORECASE)
        matches += re.findall(rf'"{kw}Name"\s*:\s*"([^"{{]+)"', combined, re.IGNORECASE)
        if matches:
            print(f"  {kw}: {list(set(matches))[:10]}")

    # 找数组形式的标签
    arr_matches = re.findall(r'"(genres?|tags?|categories?|labels?)"\s*:\s*(\[[^\]]{0,300}\])', combined, re.IGNORECASE)
    for k, v in arr_matches[:5]:
        print(f"  {k} array: {v[:200]}")

    # 3. HTML 里找标签 span/a
    print("\n--- HTML 标签元素 ---")
    # 找 badge/pill 样式的标签
    for el in soup.find_all(["span", "a"], class_=re.compile(r"tag|badge|genre|label|category|pill|chip", re.I)):
        text = el.get_text(strip=True)
        if text and 2 <= len(text) <= 30:
            print(f"  '{text}' | class: {el.get('class')}")

    # 找详情页 sidebar 或 info 里的文本
    print("\n--- 剧集信息区域 ---")
    info_els = soup.find_all(class_=re.compile(r"info|detail|meta|sidebar|desc", re.I))
    for el in info_els[:3]:
        text = el.get_text(" ", strip=True)[:200]
        if text:
            print(f"  [{el.name}.{el.get('class')}]: {text}")
