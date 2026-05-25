# -*- coding: utf-8 -*-
"""
Universal Game Translator
========================
สคริปต์แปลภาษาอัตโนมัติด้วย DeepSeek API (รองรับ CSV)
ออกแบบมาเพื่อให้ทนทานต่อ Error และใช้งานง่ายสำหรับการทำ Mod แปลภาษาทั่วไป

[ฟีเจอร์ระดับ Ultimate]:
  1. ID Tracking System (CSV): อ่านเขียนโครงสร้าง CSV 100% รักษาลำดับบรรทัดและ ID เป๊ะๆ
  2. Smart Tag Masking: ปกป้องแท็กทั้งหมด (<font>, <br>, {0}, [Action], %s) อย่างอัจฉริยะ
  3. Batch Translation Engine: แปลทีละกลุ่มพร้อมระบบ Retry อัตโนมัติ (หนี Rate Limit / Timeout)
  4. Atomic Save Checkpoint: เซฟไฟล์ลง .tmp ก่อนเขียนทับจริง ป้องกันข้อมูลหายเวลาเน็ตหลุด
  5. Hallucination Block: ตรวจจับคำที่ AI ชอบหลอน (Canary Words) และบล็อกไม่ให้เซฟลงไฟล์
  6. File Logging: บันทึกประวัติการทำงานและข้อผิดพลาดลงไฟล์ log อัตโนมัติ
"""

import csv
import time
import requests
import os
import re
import warnings
import logging
import json
from datetime import datetime

warnings.filterwarnings("ignore")

# ==============================================================================
# [ส่วนที่ 1: โหลดการตั้งค่าจากไฟล์]
# ==============================================================================
CONFIG_FILE = "config.json"

try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
except Exception as e:
    print(f"[CRITICAL ERROR] ไม่สามารถโหลดไฟล์ {CONFIG_FILE} ได้! ({e})")
    print("กรุณาตรวจสอบว่ามีไฟล์ config.json อยู่ในโฟลเดอร์เดียวกันและตั้งค่าถูกต้อง")
    exit(1)

API_KEY = config['api_settings'].get('api_key', "")
DEEPSEEK_URL = config['api_settings'].get('deepseek_url', "https://api.deepseek.com/chat/completions")
MODEL = config['api_settings'].get('model', "deepseek-chat")
TEMPERATURE = config['api_settings'].get('temperature', 0.3)
MAX_TOKENS = config['api_settings'].get('max_tokens', 8192)
MAX_RETRIES = config['api_settings'].get('max_retries', 5)
RETRY_BASE_S = config['api_settings'].get('retry_base_s', 5)
BATCH_TARGET_CHARS = config['api_settings'].get('batch_target_chars', 3000)

INPUT_CSV = config['file_settings'].get('input_csv', "input.csv")
OUTPUT_CSV = config['file_settings'].get('output_csv', "output_translated.csv")
LOG_FILE = config['file_settings'].get('log_file', "translation_log.txt")
SYSTEM_PROMPT_FILE = config['file_settings'].get('system_prompt_file', "system_prompt.txt")

CANARY_WORDS = config['safety_settings'].get('canary_words', [])

# โหลด System Prompt
try:
    with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read().strip()
except Exception as e:
    print(f"[CRITICAL ERROR] ไม่สามารถโหลดไฟล์ {SYSTEM_PROMPT_FILE} ได้! ({e})")
    exit(1)

# ==============================================================================
# [ระบบ Logging]
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ==============================================================================
# [ส่วนที่ 2: ระบบปกป้องฟังก์ชันและวิเคราะห์ประโยค]
# ==============================================================================

def is_thai(text):
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'[\u0E00-\u0E7F]', text))

def mask_tags(text):
    # ป้องกันตัวแปรเกมทุกรูปแบบ
    tag_pattern = r'(<[^>]+>|\\n|\\r|\n|\r|%[sdiefg]|\{\d+\}|\[[^\]]+\])'
    tags = re.findall(tag_pattern, text)

    masked_text = text
    placeholders = {}
    for idx, tag in enumerate(tags):
        placeholder = f"[TAG_{idx}]"
        if placeholder not in placeholders:
            placeholders[placeholder] = tag
        masked_text = masked_text.replace(tag, placeholder, 1)

    return masked_text, placeholders

def unmask_tags(translated_text, placeholders):
    unmasked = translated_text
    for placeholder, original_tag in placeholders.items():
        unmasked = unmasked.replace(placeholder, original_tag)
    return unmasked

# ==============================================================================
# [ส่วนที่ 3: ระบบเชื่อมต่อ API & ประมวลผลกลุ่มข้อความ (Batch Engine)]
# ==============================================================================

def translate_batch(batch_tasks, batch_num, total_batches):
    lines = []
    for task in batch_tasks:
        lines.append(f'"{task["id"]}"\t"{task["masked_text"]}"')
    user_prompt = f"Translate these {len(batch_tasks)} entries:\n" + "\n".join(lines)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=120)

            if response.status_code == 429:
                sleep_time = RETRY_BASE_S * (2 ** (attempt - 1))
                logging.warning(f"[429] Rate Limit ชน! นอนรอ {sleep_time} วินาที... (รอบที่ {attempt}/{MAX_RETRIES})")
                time.sleep(sleep_time)
                continue

            if response.status_code == 401:
                logging.error("[401] API Key ไม่ถูกต้องหรือหมดอายุ กรุณาตรวจสอบ API_KEY ครับ!")
                return None

            if response.status_code != 200:
                logging.error(f"[HTTP {response.status_code}] เกิดข้อผิดพลาดจากเซิร์ฟเวอร์: {response.text[:200]}")
                time.sleep(RETRY_BASE_S)
                continue

            res_json = response.json()
            if not res_json.get('choices'):
                logging.error(f"[ERROR] API ตอบกลับผิดปกติ (ไม่มี choices): {res_json}")
                time.sleep(RETRY_BASE_S)
                continue

            reply = res_json['choices'][0]['message']['content'].strip()

            # สแกนหาคำหลอน
            for bad_word in CANARY_WORDS:
                if bad_word in reply:
                    logging.warning(f"[WARNING] ตรวจเจอคำหยาบหลอนจาก AI: '{bad_word}'! บล็อกการบันทึก!")
                    return None

            reply = re.sub(r'^```[^\n]*\n?', '', reply, flags=re.MULTILINE)
            reply = re.sub(r'\n?```$', '', reply, flags=re.MULTILINE)

            results = {}
            for line in reply.split('\n'):
                line = line.strip()
                if not line or '\t' not in line:
                    continue
                parts = line.split('\t', 1)
                if len(parts) < 2:
                    continue
                res_id    = parts[0].strip().strip('"')
                res_thai  = parts[1].strip().strip('"')
                results[res_id] = res_thai

            if len(results) < len(batch_tasks):
                missing = len(batch_tasks) - len(results)
                logging.warning(f"[WARN] AI ตอบกลับมาไม่ครบ: ขาดหาย {missing} รายการ")

            return results

        except requests.exceptions.Timeout:
            logging.warning(f"[TIMEOUT] หมดเวลาเชื่อมต่อ รอบที่ {attempt}/{MAX_RETRIES} — รอ...")
            time.sleep(RETRY_BASE_S * (2 ** (attempt - 1)))
        except requests.exceptions.ConnectionError:
            logging.warning(f"[CONNECTION ERROR] ไม่สามารถเชื่อมต่อ API รอบที่ {attempt}/{MAX_RETRIES} — รอ...")
            time.sleep(RETRY_BASE_S * (2 ** (attempt - 1)))
        except Exception as e:
            logging.error(f"[ERROR] ข้อผิดพลาดไม่คาดคิด: {e} — รอ...")
            time.sleep(RETRY_BASE_S * (2 ** (attempt - 1)))

    logging.error(f"[FAIL] หมดรอบ Retry ({MAX_RETRIES} ครั้ง) สำหรับ Batch นี้")
    return None

def save_checkpoint(master_dict, keys_order, filepath):
    tmp_file = filepath + ".tmp"
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(tmp_file, 'w', encoding='utf-8') as f:
            for k in keys_order:
                val = master_dict.get(k, "")
                if val is None:
                    val = ""
                # Escape internal quotes with double quotes
                val_str = str(val).replace('"', '""')
                f.write(f'{k},"{val_str}"\n')
        os.replace(tmp_file, filepath)
    except Exception as e:
        logging.error(f"[ERROR] บันทึกไฟล์ไม่สำเร็จ: {e}")
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        raise

# ==============================================================================
# [ส่วนที่ 4: ฟังก์ชันหลักการทำงาน]
# ==============================================================================

def main():
    logging.info("=" * 60)
    logging.info("          Universal Game Translator")
    logging.info("=" * 60)

    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        logging.error("[CRITICAL] ยังไม่ได้ใส่ API_KEY ในไฟล์ config.json!")
        return

    # 1. โหลดข้อมูลเดิม
    master_dict = {}
    if os.path.exists(OUTPUT_CSV):
        logging.info(f"[1/4] พบไฟล์คลังแปลเดิม: {OUTPUT_CSV}")
        with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    master_dict[row[0]] = row[1]
        logging.info(f"      โหลดคำแปลเดิมขึ้นระบบสำเร็จ: {len(master_dict):,} รายการ")
    else:
        logging.info(f"[1/4] เตรียมสร้างไฟล์ใหม่: {OUTPUT_CSV}")

    # 2. โหลดต้นฉบับ
    if not os.path.exists(INPUT_CSV):
        logging.error(f"[ERROR] ไม่พบไฟล์ต้นฉบับ: {INPUT_CSV}")
        return

    keys_order = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                key = row[0]
                val = row[1]
                keys_order.append(key)
                if key not in master_dict:
                    master_dict[key] = val

    logging.info(f"[2/4] ผสานข้อมูลเสร็จสิ้น: รวมทั้งสิ้น {len(keys_order):,} รายการ")

    # 3. เตรียมข้อมูล
    pending_tasks = []
    for string_id in keys_order:
        text = master_dict[string_id]
        
        if is_thai(text) or not text.strip():
            continue
            
        if re.match(r'^\{\d+\}$', text.strip()):
            continue
            
        masked_text, placeholders = mask_tags(text)
        
        stripped_masked = re.sub(r'\[TAG_\d+\]', '', masked_text).strip()
        if not stripped_masked:
            continue

        pending_tasks.append({
            "id": string_id,
            "masked_text": masked_text,
            "placeholders": placeholders,
            "raw_key": string_id
        })

    logging.info(f"[3/4] มีข้อความรอแปลทั้งสิ้น: {len(pending_tasks):,} รายการ")
    if not pending_tasks:
        logging.info("      แปลครบ 100% แล้วครับ!")
        return

    batches = []
    current_batch = []
    current_chars = 0

    for task in pending_tasks:
        current_batch.append(task)
        current_chars += len(task["masked_text"])
        if current_chars >= BATCH_TARGET_CHARS:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0
    if current_batch:
        batches.append(current_batch)

    logging.info(f"      แบ่งเป็น {len(batches)} กลุ่มเพื่อประหยัด API")
    logging.info("\n[4/4] เริ่มเดินเครื่องแปลภาษา...")

    translated_count = 0
    failed_count = 0
    start_time = time.time()

    for idx, batch in enumerate(batches, 1):
        elapsed = time.time() - start_time
        logging.info(f"\n  --- กำลังรันกลุ่มที่ {idx}/{len(batches)} --- (เวลาที่ใช้ {int(elapsed//60)} น. {int(elapsed%60)} ว.)")

        api_results = translate_batch(batch, idx, len(batches))

        if api_results is None:
            failed_count += len(batch)
            continue

        for task in batch:
            tid = task["id"]
            if tid in api_results:
                thai_translation = api_results[tid]
                final_thai = unmask_tags(thai_translation, task["placeholders"])
                master_dict[task["raw_key"]] = final_thai
                translated_count += 1
            else:
                failed_count += 1

        logging.info(f"  สำเร็จสะสม: {translated_count} | ตกหล่นสะสม: {failed_count}")
        save_checkpoint(master_dict, keys_order, OUTPUT_CSV)

        if idx < len(batches):
            time.sleep(1)

    total_time = time.time() - start_time
    logging.info("\n" + "=" * 60)
    logging.info("      ปฏิบัติการแปลเสร็จสิ้น!")
    logging.info(f"  - ใช้เวลาไปทั้งสิ้น: {int(total_time//60)} นาที {int(total_time%60)} วินาที")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
