import csv
import time
import requests
import os
import re
import json
import threading

class TranslatorEngine:
    def __init__(self, log_callback=None, progress_callback=None):
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.is_running = False

    def log(self, message, level="INFO"):
        formatted_msg = f"[{level}] {message}"
        if self.log_callback:
            self.log_callback(formatted_msg)
        else:
            print(formatted_msg)

    def analyze_file(self, file_path):
        self.log("Analyzing file for auto-learning...")
        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}", "ERROR")
            return "No rules found (file not found)."

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = [row for i, row in enumerate(reader) if i < 500 and len(row) >= 2]
        except Exception as e:
            self.log(f"Error reading file: {e}", "ERROR")
            return "No rules found (read error)."

        # Scan for patterns
        found_tags = set()
        for row in rows:
            text = row[1]
            tags = re.findall(r'(<[^>]+>|\n|\r|%[sdiefg]|\{\d+\}|\[[^\]]+\])', text)
            for t in tags:
                if t not in found_tags:
                    found_tags.add(t)

        if found_tags:
            self.log(f"Detected tags/variables: {', '.join(found_tags)}")
            rules = "\n=== 4. AUTO-LEARNED RULES ===\n"
            rules += "- IMPORTANT: Ensure the following tags/variables remain exactly as they appear in the source text: "
            rules += ", ".join(found_tags) + "\n"
            return rules
        else:
            self.log("No specific tags or variables detected in the first 500 rows.")
            return ""

    def mask_tags(self, text):
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

    def unmask_tags(self, translated_text, placeholders):
        unmasked = translated_text
        for placeholder, original_tag in placeholders.items():
            unmasked = unmasked.replace(placeholder, original_tag)
        return unmasked

    def save_checkpoint(self, master_dict, keys_order, filepath):
        tmp_file = filepath + ".tmp"
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(tmp_file, 'w', encoding='utf-8') as f:
                for k in keys_order:
                    val = master_dict.get(k, "")
                    val_str = str(val).replace('"', '""')
                    f.write(f'{k},"{val_str}"\n')
        except Exception as e:
            self.log(f"Save .tmp failed: {e}", "ERROR")
            return

        try:
            os.replace(tmp_file, filepath)
        except Exception as e:
            self.log(f"Replace original file failed: {e}", "ERROR")

    def run_translation(self, config):
        self.is_running = True
        threading.Thread(target=self._process_translation, args=(config,), daemon=True).start()

    def stop_translation(self):
        if self.is_running:
            self.is_running = False
            self.log("Stopping translation process... (Will stop after current batch)")

    def _process_translation(self, config):
        api_key = config.get("api_key", "")
        model = config.get("model", "deepseek-chat")
        input_csv = config.get("input_csv", "")
        output_csv = config.get("output_csv", "")
        base_prompt = config.get("system_prompt", "")
        canary_words = [w.strip() for w in config.get("canary_words", "").split(",") if w.strip()]
        glossary = config.get("glossary", "")

        batch_target_chars = 3000
        max_retries = 5

        if not api_key:
            self.log("API Key is missing!", "ERROR")
            self.is_running = False
            return

        # Auto-Learn
        learned_rules = self.analyze_file(input_csv)
        final_system_prompt = base_prompt + "\n\n=== 3. OFFICIAL GLOSSARY ===\n" + glossary + "\n" + learned_rules
        self.log("System prompt compiled successfully.")

        master_dict = {}
        if os.path.exists(output_csv):
            try:
                with open(output_csv, 'r', encoding='utf-8') as f:
                    for row in csv.reader(f):
                        if len(row) >= 2:
                            master_dict[row[0]] = row[1]
                self.log(f"Loaded existing translation: {len(master_dict)} items.")
            except Exception as e:
                self.log(f"Error reading output CSV: {e}", "ERROR")

        if not os.path.exists(input_csv):
            self.log(f"Input file not found: {input_csv}", "ERROR")
            self.is_running = False
            return

        keys_order = []
        try:
            with open(input_csv, 'r', encoding='utf-8') as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        k, v = row[0], row[1]
                        keys_order.append(k)
                        if k not in master_dict:
                            master_dict[k] = v
        except Exception as e:
            self.log(f"Error reading input CSV: {e}", "ERROR")
            self.is_running = False
            return

        self.log(f"Total entries to process: {len(keys_order)}")

        pending_tasks = []
        for string_id in keys_order:
            text = master_dict[string_id]
            if not text.strip() or bool(re.search(r'[\u0E00-\u0E7F]', text)) or re.match(r'^\{\d+\}$', text.strip()):
                continue
            
            masked_text, placeholders = self.mask_tags(text)
            if not re.sub(r'\[TAG_\d+\]', '', masked_text).strip():
                continue

            pending_tasks.append({
                "id": string_id,
                "masked_text": masked_text,
                "placeholders": placeholders,
                "raw_key": string_id
            })

        self.log(f"Entries waiting for translation: {len(pending_tasks)}")
        
        if not pending_tasks:
            self.log("Everything is already translated!")
            if self.progress_callback:
                self.progress_callback(1.0)
            self.is_running = False
            return

        batches = []
        current_batch = []
        current_chars = 0
        for task in pending_tasks:
            current_batch.append(task)
            current_chars += len(task["masked_text"])
            if current_chars >= batch_target_chars:
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
        if current_batch:
            batches.append(current_batch)

        self.log(f"Divided into {len(batches)} batches.")

        translated_count = 0
        failed_count = 0
        total_batches = len(batches)

        for idx, batch in enumerate(batches, 1):
            if not self.is_running:
                self.log("Translation stopped by user.")
                break

            self.log(f"Processing Batch {idx}/{total_batches}...")
            
            lines = [f'"{t["id"]}"\t"{t["masked_text"]}"' for t in batch]
            user_prompt = f"Translate these {len(batch)} entries:\n" + "\n".join(lines)
            
            success = False
            for attempt in range(1, max_retries + 1):
                if not self.is_running:
                    break
                try:
                    reply = ""
                    # --- NATIVE API ROUTING ---
                    if model.startswith("gemini"):
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                        payload = {
                            "systemInstruction": {"parts": [{"text": final_system_prompt}]},
                            "contents": [{"parts": [{"text": user_prompt}]}],
                            "generationConfig": {"temperature": 0.3}
                        }
                        res = requests.post(url, json=payload, timeout=120)
                        if res.status_code == 429:
                            self.log(f"[429] Rate Limit. Waiting... (Attempt {attempt}/{max_retries})", "WARN")
                            time.sleep(5)
                            continue
                        if res.status_code != 200:
                            self.log(f"Gemini API Error {res.status_code}: {res.text[:100]}", "ERROR")
                            time.sleep(5)
                            continue
                        reply = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

                    elif model.startswith("claude"):
                        url = "https://api.anthropic.com/v1/messages"
                        headers = {
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        }
                        payload = {
                            "model": model,
                            "max_tokens": 8192,
                            "temperature": 0.3,
                            "system": final_system_prompt,
                            "messages": [{"role": "user", "content": user_prompt}]
                        }
                        res = requests.post(url, json=payload, headers=headers, timeout=120)
                        if res.status_code == 429:
                            self.log(f"[429] Rate Limit. Waiting... (Attempt {attempt}/{max_retries})", "WARN")
                            time.sleep(5)
                            continue
                        if res.status_code != 200:
                            self.log(f"Claude API Error {res.status_code}: {res.text[:100]}", "ERROR")
                            time.sleep(5)
                            continue
                        reply = res.json()["content"][0]["text"].strip()

                    else:
                        # OpenAI / DeepSeek format
                        if model.startswith("deepseek"):
                            url = "https://api.deepseek.com/chat/completions"
                        else:
                            url = "https://api.openai.com/v1/chat/completions"
                            
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": model,
                            "messages": [
                                {"role": "system", "content": final_system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.3,
                        }
                        if model.startswith("gpt-4") or model.startswith("deepseek"):
                            payload["max_tokens"] = 8192
                            
                        res = requests.post(url, json=payload, headers=headers, timeout=120)
                        if res.status_code == 429:
                            self.log(f"[429] Rate Limit. Waiting... (Attempt {attempt}/{max_retries})", "WARN")
                            time.sleep(5)
                            continue
                        if res.status_code == 401:
                            self.log("Unauthorized (401). Invalid API Key.", "ERROR")
                            self.is_running = False
                            break
                        if res.status_code != 200:
                            self.log(f"API Error {res.status_code}: {res.text[:100]}", "ERROR")
                            time.sleep(5)
                            continue
                        reply = res.json()['choices'][0]['message']['content'].strip()
                    # --- END ROUTING ---
                    
                    # Canary check
                    canary_hit = False
                    for cw in canary_words:
                        if cw in reply:
                            self.log(f"Detected hallucinated word: {cw}. Rejecting batch.", "WARN")
                            canary_hit = True
                            break
                    if canary_hit:
                        time.sleep(2)
                        continue

                    reply = re.sub(r'^```[^\n]*\n?', '', reply, flags=re.MULTILINE)
                    reply = re.sub(r'\n?```$', '', reply, flags=re.MULTILINE)

                    results = {}
                    for line in reply.split('\n'):
                        line = line.strip()
                        if '\t' in line:
                            parts = line.split('\t', 1)
                            if len(parts) >= 2:
                                results[parts[0].strip().strip('"')] = parts[1].strip().strip('"')

                    for task in batch:
                        tid = task["id"]
                        if tid in results:
                            final_thai = self.unmask_tags(results[tid], task["placeholders"])
                            master_dict[task["raw_key"]] = final_thai
                            translated_count += 1
                        else:
                            failed_count += 1

                    success = True
                    break

                except Exception as e:
                    self.log(f"Request Error: {e}", "ERROR")
                    time.sleep(5)

            if not success and self.is_running:
                self.log(f"Batch {idx} failed after {max_retries} attempts.", "ERROR")
                failed_count += len(batch)

            self.save_checkpoint(master_dict, keys_order, output_csv)
            if self.progress_callback:
                self.progress_callback(idx / total_batches)
            
            if self.is_running and idx < total_batches:
                time.sleep(1)

        self.log(f"Operation Finished! Translated: {translated_count}, Failed: {failed_count}")
        if self.progress_callback:
            self.progress_callback(1.0)
        self.is_running = False
