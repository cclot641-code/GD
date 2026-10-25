import os
import re
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
import requests

PRODUCT_CODE = "4570118196217"
URL = f"https://gashapon.jp/shop/gplus_list.php?product_code={PRODUCT_CODE}"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def check_stock():
    # 1. 強制強制轉換並取得日本時間 (JST, UTC+9)
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    current_hour = now_jst.hour
    current_minute = now_jst.minute
    current_total_minutes = current_hour * 60 + current_minute

    # 2. 設定運作時間範圍：07:00 至 24:00 (即 420 分鐘到 1440 分鐘)
    start_limit = 7 * 60      # 07:00
    end_limit = 24 * 60       # 24:00

    print(f"目前檢測到的日本時間 (JST): {now_jst.strftime('%H:%M')}")

    if not (start_limit <= current_total_minutes < end_limit):
        print(f"目前時間不在營運時間內 (07:00 - 24:00)，跳過執行。")
        return

    print("目前時間在營運時間內，開始執行爬蟲...")

    # (以下保持原本的 Playwright 爬蟲與 Discord 發送邏輯不變...)
