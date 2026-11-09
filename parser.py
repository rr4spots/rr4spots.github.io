import requests
import json
import re
import os
import time
from datetime import datetime

VK_TOKEN = os.environ.get("VK_TOKEN")

VK_GROUPS = [
    "rr4mestakleva", 
    "pp4farmtrof", 
    "rr4pepper", 
    "pp4wikipedia", 
    "rf4map"
]

def normalize_wb(name):
    if not name:
        return "Не указан"
    n = name.lower()
    if "комарин" in n: return "оз. Комариное"
    if "лосин" in n: return "оз. Лосиное"
    if "вьюн" in n: return "р. Вьюнок"
    if "острог" in n: return "оз. Старый Острог"
    if "бела" in n or "белая" in n: return "р. Белая"
    if "куори" in n: return "оз. Куори"
    if "медное" in n: return "оз. Медное"
    if "медвеж" in n: return "оз. Медвежье"
    if "волхов" in n: return "р. Волхов"
    if "донец" in n: return "р. Северский Донец"
    if "сура" in n or "суру" in n: return "р. Сура"
    if "архипелаг" in n: return "Ладожский архипелаг"
    if "ладожск" in n or "ладога" in n: return "Ладожское оз."
    if "янтар" in n: return "оз. Янтарное"
    if "ахтуб" in n: return "р. Ахтуба"
    if "тунгус" in n: return "р. Нижняя Тунгуска"
    if "яма" in n or "яму" in n: return "р. Яма"
    if "норвеж" in n or "море" in n or "банка" in n: return "Норвежское море"
    if any(c in name for c in ['@', '#', '\n', '\r']) or len(name) > 30 or any(x in n for x in ["водоем", "не указан"]):
        return "Не указан"
    return name.title()

def clean_text(text):
    if not text:
        return ""
    # Удаляем ссылки и чужие каналы
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'(?:t\.me|vk\.com|vk\.me|rf4-map\.ru|rf4stat\.ru)\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'@[a-zA-Z0-9_]+', '', text)
    text = re.sub(r'#[a-zA-Zа-яА-ЯёЁ0-9_]+', '', text)

    promo_patterns = [
        r'(?i)наш\s+(?:telegram|тг|канал|паблик|сайт|дискорд|discord)[^\n\r]*',
        r'(?i)сайт с полезной информацией[^\n\r]*',
        r'(?i)вся информация по рр4[^\n\r]*',
        r'(?i)подписывайтесь[^\n\r]*',
        r'(?i)правила публикации[^\n\r]*',
        r'(?i)беседка группы[^\n\r]*',
        r'(?i)добавить пост[^\n\r]*',
        r'(?i)понравился пост[^\n\r]*',
        r'(?i)бот для поиска[^\n\r]*',
        r'(?i)все точки в тг[^\n\r]*',
        r'(?i)предложить пост[^\n\r]*',
        r'(?i)поиск точки[^\n\r]*',
        r'(?i)больше точек[^\n\r]*',
    ]
    for pat in promo_patterns:
        text = re.sub(pat, '', text)

    stop_words = [
        "- Автор:", "Автор:", "ПРЕДЛОЖИТЬ ПОСТ", "ПОИСК ТОЧКИ", 
        "БОЛЬШЕ ТОЧЕК", "СПАСИБО", "Условия:", "ПРЕДЛОЖИТЬ", 
        "Понравился пост?", "Обновление игры"
    ]
    for word in stop_words:
        if word in text:
            text = text.split(word)[0]

    text = re.sub(r'Водо[её]м:\s*-\s*', '', text)
    text = re.sub(r'^[ :—\-|]+', '', text)
    text = text.replace('|  |', '|').replace('| - |', '|').replace('-  -', '-').strip(' |-\n\r')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_vk():
    spots_file = 'spots.json'
    old_spots = {}
    if os.path.exists(spots_file):
        try:
            with open(spots_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for spot in data:
                    old_spots[spot['id']] = spot
            print(f"Загружено из базы: {len(old_spots)} старых точек.")
        except Exception as e:
            print(f"Ошибка чтения старой базы: {e}")

    print("Подключаемся к VKontakte...")
    new_posts_found = 0
    if not VK_TOKEN:
        print("Предупреждение: Токен ВК не найден, парсинг ВК пропущен.")
    else:
        url = "https://api.vk.com/method/wall.get"
        for group in VK_GROUPS:
            print(f"\n--- Парсинг группы: {group} ---")
            for offset in [0, 100, 200]:
                try:
                    time.sleep(1)  # Пауза 1 сек, чтобы не срабатывал Flood control ВК
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    }
                    params = {
                        "domain": group, 
                        "count": 100,
                        "offset": offset,
                        "access_token": VK_TOKEN,  
                        "v": "5.193"               
                    }
                    response = requests.get(url, params=params, headers=headers, timeout=15).json()

                    if "error" in response:
                        print(f"[-] Ошибка ВК ({group}): {response['error']['error_msg']}")
                        break

                    for post in response.get("response", {}).get("items", []):
                        post_id = f"{group}_{post.get('id')}"
                        
                        if post_id in old_spots:
                            if post.get("date", 0) > time.time() - 7 * 86400:
                                old_spots[post_id]["likes"] = post.get("likes", {}).get("count", 0)
                                old_spots[post_id]["views"] = post.get("views", {}).get("count", 0)
                            continue

                        raw_text = post.get("text", "")
                        if not raw_text: continue

                        clean_description = clean_text(raw_text)
                        lower_clean_text = clean_description.lower()

                        spam_words = ["розыгрыш", "призовое место", "магазина", "барахолка", "купить", "промокод", "скидка", "рублей", "купон"]
                        if any(word in lower_clean_text for word in spam_words):
                            continue

                        spot_tag = "Обычная"
                        if any(word in lower_clean_text for word in ["трофей", "троф", "трофе", "синяк", "синь", "голуб", "голубая","звезд", "звёзд","⭐"]):
                            spot_tag = "Трофей"
                        elif any(word in lower_clean_text for word in ["фарм", "фар"]):
                            spot_tag = "Фарм"
                        elif any(word in lower_clean_text for word in ["высед", "высе", "высиж"]):
                            spot_tag = "Высед"

                        coords_match = re.search(r'(\d{1,3}\s*[:\-]\s*\d{1,3})', raw_text)
                        square_match = re.search(r'Квадрат:\s*([A-ZА-Я0-9\-]+)', raw_text, re.IGNORECASE)
                        if coords_match:
                            coordinates = re.sub(r'\s*[:\-]\s*', ':', coords_match.group(1).strip())
                        elif square_match:
                            coordinates = square_match.group(1).strip()
                        else:
                            continue 

                        waterbody_name = "Не указан"
                        wb_match = re.search(r'Водо[её]м:\s*([^|\n\r]+)', raw_text, re.IGNORECASE)
                        if wb_match:
                            wb_temp = wb_match.group(1).strip()
                            wb_temp = re.sub(r'@[a-zA-Z0-9_]+', '', wb_temp)
                            wb_temp = re.sub(r'#[a-zA-Zа-яА-ЯёЁ0-9_]+', '', wb_temp).strip()
                            if wb_temp and wb_temp != "-" and len(wb_temp) > 1 and not any(x in wb_temp.lower() for x in ["водоем", "не указан"]):
                                waterbody_name = wb_temp
                        
                        if waterbody_name == "Не указан":
                            tags = re.findall(r'#([a-zа-яё0-9_]+)', raw_text.lower())
                            ignore_tags = ['трофей', 'фарм', 'гайд', 'сборка', 'вопрос', 'местаклева', 'рр4', 'rr4', 'rf4map', 'pp4farmtrof', 'rr4pepper', 'pp4wikipedia']
                            for tag in tags:
                                tag = tag.replace('_rf4map', '').replace('rf4_', '').replace('pp4_', '') 
                                if tag not in ignore_tags:
                                    waterbody_name = tag
                                    break
                        
                        waterbody_name = normalize_wb(waterbody_name)

                        images_list = []
                        attachments = post.get("attachments", [])
                        for att in attachments:
                            if att["type"] == "photo":
                                sizes = att["photo"]["sizes"]
                                best_photo = max(sizes, key=lambda x: x["width"])
                                images_list.append(best_photo["url"])

                        timestamp = post.get("date", 0)
                        date_str = datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')

                        spot = {
                            "id": post_id,
                            "timestamp": timestamp,
                            "date": date_str,
                            "waterbody": waterbody_name,
                            "tag": spot_tag,
                            "coordinates": coordinates,
                            "description": clean_description,
                            "images": images_list,
                            "likes": post.get("likes", {}).get("count", 0),
                            "views": post.get("views", {}).get("count", 0)
                        }
                        
                        old_spots[post_id] = spot
                        new_posts_found += 1
                        
                except Exception as e:
                    print(f"Ошибка парсинга VK ({group}): {e}")
                    
        print(f"\nВсего добавлено новых точек из ВК: {new_posts_found}")

    # --- Загрузка одобренных точек от пользователей из Telegram бота (@rr4spotsbot) ---
    print("\n--- Загрузка точек из Telegram бота (@rr4spotsbot) ---")
    tg_points_found = 0
    try:
        tg_url = "https://rf4-spots.pronk211rf4.workers.dev/api/points"
        tg_resp = requests.get(tg_url, timeout=15)
        if tg_resp.ok:
            tg_data = tg_resp.json().get("points", [])
            for pt in tg_data:
                coords = str(pt.get('coordinates') or '').strip()
                if pt.get('id') in ['8c5c9204bbee', 'feef46abbe17', '0ebfa0d0f760'] or not coords or coords == '1' or ':' not in coords:
                    continue  # Игнорируем тестовые точки без координат
                spot_id = f"tg_{pt['id']}"
                if spot_id not in old_spots:
                    ts = int(time.time())
                    date_str = datetime.now().strftime("%d.%m.%Y")
                    if pt.get("approved_at"):
                        try:
                            clean_iso = pt["approved_at"].split(".")[0]
                            dt = datetime.strptime(clean_iso, "%Y-%m-%dT%H:%M:%S")
                            ts = int(dt.timestamp())
                            date_str = dt.strftime("%d.%m.%Y")
                        except Exception:
                            pass

                    clean_wb = normalize_wb(pt.get("waterbody", ""))
                    goal_text = pt.get("goal_label") or pt.get("goal") or "Трофей"
                    if goal_text == "trophy": goal_text = "Трофей"
                    elif goal_text == "farm": goal_text = "Фарм"
                    elif goal_text == "spawn": goal_text = "Высед"

                    desc = clean_text(pt.get("site_text") or pt.get("description", ""))

                    old_spots[spot_id] = {
                        "id": spot_id,
                        "timestamp": ts,
                        "date": date_str,
                        "waterbody": clean_wb,
                        "tag": goal_text,
                        "coordinates": pt.get("coordinates", ""),
                        "description": desc,
                        "images": pt.get("photos", []),
                        "likes": 50,
                        "views": 200
                    }
                    tg_points_found += 1
            print(f"Добавлено новых точек из Telegram: {tg_points_found}")
        else:
            print(f"Ошибка обращения к API бота: HTTP {tg_resp.status_code}")
    except Exception as e:
        print(f"Ошибка загрузки точек бота: {e}")

    # Строгая сортировка по timestamp убыванию (самые свежие даты всегда сверху)
    all_spots = list(old_spots.values())
    all_spots.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    # Ограничиваем топ 3000 активных точек для быстродействия сети
    all_spots = all_spots[:3000]

    with open(spots_file, 'w', encoding='utf-8') as f:
        json.dump(all_spots, f, ensure_ascii=False, indent=2)
        
    print(f"Готово! В базе {spots_file} сейчас {len(all_spots)} точек.")

    try:
        import calculate_verified
        calculate_verified.calculate_verified()
    except Exception as e:
        print(f"Ошибка calculate_verified: {e}")

if __name__ == "__main__":
    parse_vk()
