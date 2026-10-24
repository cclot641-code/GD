from collections import Counter
import os
import re
import urllib.parse
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def extract_city(address):
  # 從地址中擷取到「市」或「區/町/村」為止的行政區（例如：東京都八王子市、宮城県仙台市）
  match = re.search(r'(^.*?[都道府県].+?[市])', address)
  if match:
    return match.group(1)
  # 備用匹配
  match_alt = re.search(r'(^.+?[都道府県][^0-9]+?[市区町村])', address)
  if match_alt:
    full = match_alt.group(1)
    # 如果包含市，截取到市為止讓格式更整齊
    idx = full.find("市")
    if idx != -1:
      return full[: idx + 1]
    return full
  return "其他地區"


def check_stock():
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()

    try:
      page.goto(URL, timeout=30000)
      page.wait_for_selector("body", timeout=10000)
      page.wait_for_timeout(4000)

      # 抓取頁面所有文字行
      shop_data = page.evaluate("""() => {
                const bodyText = document.body.innerText;
                return bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            }""")

      browser.close()

      shops_list = []
      i = 0
      while i < len(shop_data):
        line = shop_data[i]

        footer_keywords = [
            "スケジュール",
            "キャラクター",
            "ブランド",
            "ショップ",
            "ログイン",
            "さがす",
            "閉じる",
            "ホーム>",
            "ご利用規約",
            "プライバシーポリシー",
            "よくあるご質問",
            "お問合せ",
            "アンケート",
            "ウェブアクセシビリティ",
            "Do Not Sell",
            "BANDAI",
            "NAMCO",
            "無断転用",
            "登録商標",
            "コピーライト",
            "©",
            "All Rights Reserved",
        ]

        if any(fk in line for fk in footer_keywords) and not (
            "店" in line or "デパート" in line
        ):
          i += 1
          continue

        if (
            "ガシャポン" in line or "デパート" in line or "店" in line
        ) and len(line) < 80:
          shop_name = line
          address = ""

          for j in range(1, 4):
            if i + j < len(shop_data):
              next_line = shop_data[i + j]
              if any(
                  p in next_line
                  for p in ["都", "道", "府", "県", "市", "区", "町", "村"]
              ) and not any(fk in next_line for fk in footer_keywords):
                address = next_line
                break

          if address:
            city = extract_city(address)
          else:
            city = "未知地區"

          # 產生 Google 地圖導航網址
          map_query = urllib.parse.quote(f"{shop_name} {address}")
          map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"

          shops_list.append(
              {"name": shop_name, "address": address, "city": city, "url": map_url}
          )
        i += 1

      if shops_list:
        # 統計各城市的店舖數量
        city_counts = Counter([s["city"] for s in shops_list])
        summary_str = "/".join([f"{city}({count})" for city, count in city_counts.items()])

        # 組裝發送到 Discord 的訊息
        content = f"🚨 **【扭蛋庫存即時更新】** 🚨\n{summary_str}\n\n------------------\n"

        entries = []
        for s in shops_list:
          entry = f"📍 **{s['name']}**\n🏠 地址：{s['address']}\n🔗 [Google地圖導航]({s['url']})"
          entries.append(entry)

        content += "\n\n".join(entries)
        content += f"\n\n🔗 官方查詢頁面：\n{URL}"
      else:
        content = f"🔍 目前頁面未偵測到有貨店舖，請點擊連結確認：\n{URL}"

      send_to_discord(content)

    except Exception as e:
      browser.close()
      print(f"爬取發生錯誤: {e}")


def send_to_discord(message):
  if not DISCORD_WEBHOOK_URL:
    print("未設定 Discord Webhook")
    return

  data = {"content": message}
  requests.post(DISCORD_WEBHOOK_URL, json=data)


if __name__ == "__main__":
  check_stock()
