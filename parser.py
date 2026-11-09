import requests
import json
import re
import os
import time
import subprocess
import shutil
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

def norm_coords(c):
    if not c:
        return ""
    c = str(c).strip()
    m = re.search(r'(\d{1,3})\s*[:\-]\s*(\d{1,3})', c)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return re.sub(r'\s+', ' ', c).lower()

def clean_text(text):
    if not text:
        return ""
    # Удаляем любые внешние ссылки, Telegram каналы, группы ВК и домены конкурентов
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'(?:t\.me|vk\.com|vk\.me|rf4-map\.ru|rf4stat\.ru)\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'@[a-zA-Z0-9_]+', '', text)
    text = re.sub(r'#[a-zA-Zа-яА-ЯёЁ0-9_]+', '', text)

    # Удаляем точечные рекламные и сервисные строки без повреждения полезного текста
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

def extract_fish(text, display_fish=""):
    if display_fish and isinstance(display_fish, str):
        return display_fish.strip().lower()
    if not text:
        return ""
    cleaned = text.replace('\ufe0f', '').replace('\u200d', '')
    m = re.search(r'Рыба\s*[:\-–]?\s*([A-Za-zА-Яа-яЁё\s,]+?)(?=[-\n\r📌🎣💧📝]|Координаты|Квадрат|$)', cleaned, re.IGNORECASE)
    if m:
        val = m.group(1).strip().strip(':-, ')
        if 1 < len(val) < 80:
            return val.lower()
    m2 = re.search(r'[⭐👑🐟🦈🐠]\s*([A-Za-zА-Яа-яЁё\s,]+?)(?=[-\n\r📌🎣💧📝]|Координаты|$)', cleaned)
    if m2:
        val = m2.group(1).strip().strip(':-, ')
        if 1 < len(val) < 80 and not any(w in val.lower() for w in ['фарм', 'точка', 'водоем']):
            return val.lower()
    return ""

def text_signature(text):
    if not text:
        return set()
    cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s]', ' ', text.lower())
    stop = {'в', 'на', 'с', 'по', 'за', 'и', 'для', 'из', 'от', 'до', 'не', 'озеро', 'река', 'точка', 'водоем', 'рр4', 'rf4', 'нормальная', 'температура', 'воды', 'координаты', 'клипса', 'квадрат'}
    return {w for w in cleaned.split() if len(w) > 2 and w not in stop}

def text_similarity(t1, t2):
    s1, s2 = text_signature(t1), text_signature(t2)
    if not s1 or not s2:
        return 0.0
    inter = s1 & s2
    min_len = min(len(s1), len(s2))
    return len(inter) / min_len if min_len > 0 else 0.0

def get_source_priority(spot):
    sid = spot.get('id', '').lower()
    desc = spot.get('description', '').lower()
    # 1. Точки из собственного бота пользователя @rr4spotsbot (наивысший приоритет, чистые оригиналы)
    if sid.startswith('tg_') and not any(k in sid for k in ['tg_rf4map', 'tg_psixgame']):
        return 100
    # 2. Discord rf4stat (чистые скриншоты игроков)
    if 'rf4stat' in sid or 'discord' in sid:
        return 90
    # 3. WeChat (чистые китайские скриншоты)
    if 'wechat' in sid:
        return 85
    # 4. ВК группы без чужих логотипов
    if any(grp in sid for grp in ['rr4mestakleva', 'pp4farmtrof', 'rr4pepper', 'pp4wikipedia']):
        return 80
    # 5. Каналы с водяным знаком RF4 MAP (низший приоритет, их фото замещаются оригиналами)
    if 'rf4map' in sid or 'rf4-map' in desc or 't.me/rf4map' in desc:
        return 20
    return 50

def get_image_key(url):
    if not url:
        return ""
    # Очищаем параметры качества ВК и вычленяем уникальный хэш файла
    u = re.sub(r'\?.*$', '', url)
    parts = u.rstrip('/').split('/')
    return parts[-1] if parts else u

def merge_two_spots(spot1, spot2):
    p1 = get_source_priority(spot1)
    p2 = get_source_priority(spot2)
    
    primary = spot1 if p1 >= p2 else spot2
    secondary = spot2 if p1 >= p2 else spot1
    
    # Объединяем фото: чистые фото из первоисточника идут первыми
    merged_images = []
    seen_imgs = set()
    for img in primary.get('images', []):
        k = get_image_key(img)
        if k and k not in seen_imgs:
            seen_imgs.add(k)
            merged_images.append(img)
    for img in secondary.get('images', []):
        k = get_image_key(img)
        if k and k not in seen_imgs:
            seen_imgs.add(k)
            merged_images.append(img)
            
    # Ограничиваем галерею максимум 8 лучшими фото (чистые всегда идут первыми)
    merged_images = merged_images[:8]

    # Выбираем более полное и информативное описание
    d1 = primary.get('description', '').strip()
    d2 = secondary.get('description', '').strip()
    merged_desc = d1 if len(d1) >= len(d2) else d2
    
    # Лайки и просмотры: берём максимум
    merged_likes = max(primary.get('likes', 0), secondary.get('likes', 0))
    merged_views = max(primary.get('views', 0), secondary.get('views', 0))
    
    # Цель/тег: сохраняем более ценный тег
    tags = [primary.get('tag'), secondary.get('tag')]
    if 'Трофей' in tags: merged_tag = 'Трофей'
    elif 'Фарм' in tags: merged_tag = 'Фарм'
    elif 'Высед' in tags: merged_tag = 'Высед'
    else: merged_tag = primary.get('tag') or 'Обычная'
    
    return {
        "id": primary.get('id'),
        "timestamp": max(primary.get('timestamp', 0), secondary.get('timestamp', 0)),
        "date": primary.get('date') or secondary.get('date'),
        "waterbody": primary.get('waterbody'),
        "tag": merged_tag,
        "coordinates": primary.get('coordinates'),
        "description": merged_desc,
        "images": merged_images,
        "likes": merged_likes,
        "views": merged_views
    }

def deduplicate_all_spots(spots_list):
    from collections import defaultdict
    groups = defaultdict(list)
    for s in spots_list:
        wb = normalize_wb(s.get('waterbody'))
        c = norm_coords(s.get('coordinates'))
        groups[(wb, c)].append(s)

    merged_total = 0
    clean_spots = []

    for key, spot_group in groups.items():
        if len(spot_group) == 1:
            clean_spots.append(spot_group[0])
            continue
            
        cluster = []
        for s in spot_group:
            matched = False
            t_s = s.get('timestamp', 0)
            fish_s = extract_fish(s.get('description', ''))
            
            for idx, existing in enumerate(cluster):
                t_e = existing.get('timestamp', 0)
                time_diff = abs(t_s - t_e)
                
                # Проверка временного окна и признаков дубликата
                if time_diff <= 86400 or (time_diff <= 172800 and (image_overlap or id_match or sim >= 0.65)):
                    fish_e = extract_fish(existing.get('description', ''))
                    sim = text_similarity(s.get('description', ''), existing.get('description', ''))
                    fish_match = bool(fish_s and fish_e and (fish_s in fish_e or fish_e in fish_s))
                    image_overlap = bool(set(get_image_key(img) for img in s.get('images', [])) & set(get_image_key(img) for img in existing.get('images', [])))
                    
                    id_match = (('rf4map' in s.get('id', '') and 'rf4map' in existing.get('id', '')) and any(num in existing.get('id', '') for num in re.findall(r'\d{4,6}', s.get('id', ''))))
                    
                    if fish_match or sim >= 0.40 or image_overlap or id_match:
                        cluster[idx] = merge_two_spots(existing, s)
                        matched = True
                        merged_total += 1
                        break
            if not matched:
                cluster.append(s)
        clean_spots.extend(cluster)

    print(f"[Дедупликация] Объединено повторных постов: {merged_total}. Уникальных точек: {len(clean_spots)}")
    return clean_spots

def parse_vk(old_spots):
    print("Подключаемся к VKontakte...")
    new_posts_found = 0
    if not VK_TOKEN:
        print("Предупреждение: Токен ВК не найден, парсинг ВК пропущен.")
        return 0

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
    return new_posts_found

def parse_telegram_bot(old_spots):
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
    return tg_points_found

def parse_farmtrof(old_spots):
    print("\n--- Синхронизация базы точек rr4farmtrof (Discord, WeChat, VK) ---")
    raw_data = None
    
    # Сначала пробуем системный curl (быстро и надежно обходит блокировки)
    try:
        curl_bin = shutil.which("curl") or shutil.which("curl.exe")
        if curl_bin:
            cmd = [curl_bin, "-s", "--compressed", "--max-time", "30", "https://rr4farmtrof.com/assets/data/points-preview.json"]
            res = subprocess.run(cmd, capture_output=True, timeout=35)
            if res.returncode == 0 and res.stdout and len(res.stdout) > 1000:
                raw_data = json.loads(res.stdout.decode('utf-8'))
                print(f"[Farmtrof] Успешно загружен JSON через curl ({len(res.stdout)} байт)")
    except Exception as e:
        print(f"[Farmtrof] Ошибка curl загрузки: {e}")

    # Запасной вариант через requests
    if not raw_data:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*"
            }
            resp = requests.get("https://rr4farmtrof.com/assets/data/points-preview.json", headers=headers, timeout=20)
            if resp.ok:
                raw_data = resp.json()
                print(f"[Farmtrof] Успешно загружен JSON через requests")
        except Exception as e:
            print(f"[Farmtrof] Ошибка requests загрузки: {e}")

    if not raw_data:
        print("[-] Не удалось получить данные от rr4farmtrof.")
        return 0

    added = 0
    for item in raw_data:
        source_key = item.get('source_key', '')
        lake = item.get('display_lake') or item.get('waterbody_name') or ''
        wb = normalize_wb(lake)
        raw_loc = item.get('location', '')
        coords = norm_coords(raw_loc)
        if not coords or coords == 'на скриншоте':
            coords = raw_loc.strip() if 0 < len(raw_loc.strip()) <= 20 else 'Не указаны'
            
        text_content = item.get('cleaned_text') or item.get('post_text') or ''
        clean_desc = clean_text(text_content)
        lower_text = clean_desc.lower()
        
        tag = 'Обычная'
        if any(w in lower_text for w in ['трофей', 'троф', 'синяк', 'синь', '⭐', '10⭐']):
            tag = 'Трофей'
        elif any(w in lower_text for w in ['фарм']):
            tag = 'Фарм'
        elif any(w in lower_text for w in ['высед']):
            tag = 'Высед'
            
        post_date = item.get('post_date') or item.get('date') or ''
        ts = int(time.time())
        date_str = datetime.now().strftime('%d.%m.%Y')
        if post_date:
            try:
                dt = datetime.strptime(post_date[:19], '%Y-%m-%d %H:%M:%S')
                ts = int(dt.timestamp())
                date_str = dt.strftime('%d.%m.%Y')
            except Exception:
                try:
                    dt = datetime.strptime(post_date[:10], '%Y-%m-%d')
                    ts = int(dt.timestamp())
                    date_str = dt.strftime('%d.%m.%Y')
                except Exception:
                    pass
                    
        photos = [('https://rr4farmtrof.com' + p if p.startswith('/') else p) for p in item.get('photos', [])]
        safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', source_key) or f"ft_{item.get('site_post_id', added)}"
        spot_id = f"ft_{safe_id}"
        
        old_spots[spot_id] = {
            "id": spot_id,
            "timestamp": ts,
            "date": date_str,
            "waterbody": wb,
            "tag": tag,
            "coordinates": coords,
            "description": clean_desc,
            "images": photos,
            "likes": 25,
            "views": 150
        }
        added += 1

    print(f"Обработано точек из rr4farmtrof: {added}")
    return added

def run_pipeline():
    spots_file = 'spots.json'
    archive_file = 'spots_archive.json'
    old_spots = {}
    
    # Загружаем из полного архива, если есть, иначе из spots.json
    source_load_file = archive_file if os.path.exists(archive_file) else spots_file
    if os.path.exists(source_load_file):
        try:
            with open(source_load_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for spot in data:
                    old_spots[spot['id']] = spot
            print(f"Загружено из базы ({source_load_file}): {len(old_spots)} точек.")
        except Exception as e:
            print(f"Ошибка чтения старой базы: {e}")

    # 1. Загрузка VK постов
    parse_vk(old_spots)

    # 2. Загрузка точек от пользователей из Telegram бота
    parse_telegram_bot(old_spots)

    # 3. Загрузка точек из открытой базы Farmtrof (WeChat, Discord, VK)
    parse_farmtrof(old_spots)

    # 4. Умная дедупликация и объединение информации (Smart Merge)
    all_spots_raw = list(old_spots.values())
    clean_spots = deduplicate_all_spots(all_spots_raw)

    # Сортировка по времени (свежие сверху)
    clean_spots.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    # Сохраняем полный исторический архив без потерь
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(clean_spots, f, ensure_ascii=False, indent=2)
    print(f"Полный архив сохранен в {archive_file} ({len(clean_spots)} точек).")

    # Сохраняем оптимизированный рабочий spots.json (топ-2000 свежих точек за последние ~60 дней)
    active_spots = clean_spots[:2000]
    with open(spots_file, 'w', encoding='utf-8') as f:
        json.dump(active_spots, f, ensure_ascii=False, indent=2)
        
    print(f"Готово! В основном быстром файле {spots_file} сейчас {len(active_spots)} активных точек.")

    # 5. Автоматический пересчёт проверенных точек (verified.json)
    try:
        import calculate_verified
        calculate_verified.calculate_verified()
    except Exception as e:
        print(f"Ошибка пересчета verified.json: {e}")

if __name__ == "__main__":
    run_pipeline()
