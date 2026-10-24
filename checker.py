# 組合成乾淨的訊息格式（含地區總結）
            if shops_data:
                # 提取所有城市的簡短總結
                cities = []
                for item in shops_data:
                    # 簡單抓取地址前幾個字作為總結（例如 東京都八王子市）
                    addr = item['address']
                    for pref in ["東京都", "北海道", "京都府", "大阪府"]:
                        if pref in addr:
                            # 嘗試抓到市/區
                            parts = addr.split(pref)
                            if len(parts) > 1:
                                city_part = pref + parts[1].split()[0]
                                if city_part not in cities:
                                    cities.append(city_part)
                    for pref in ["県"]:
                        if pref in addr:
                            # 針對縣級地址處理
                            idx = addr.find(pref)
                            if idx != -1:
                                city_part = addr[:idx+1] + addr[idx+1:].split()[0]
                                if city_part not in cities:
                                    cities.append(city_part)

                summary_line = ", ".join(cities) if cities else "全國多地"

                entries = []
                for item in shops_data:
                    entries.append(f"{item['name']}\n地址：{item['address']}")
                
                content = f"🚨 **【扭蛋庫存即時更新】** 🚨\n\n📌 **{summary_line}**\n\n" + "\n\n".join(entries)
                content += f"\n\n🔗 點此查看官方清單：\n{URL}"
