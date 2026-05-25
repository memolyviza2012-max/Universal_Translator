# 📖 Universal Game Translator - v1.0 คู่มือการใช้งาน

ยินดีต้อนรับเข้าสู่ **Universal Game Translator** (by NodNuatTranslator) โปรแกรมแปลภาษาสำหรับเกมเมอร์และนักม็อดเดอร์ ที่สร้างมาเพื่อความง่าย รวดเร็ว และรองรับ AI ระดับท็อปทุกค่าย!

---

## 🚀 1. การเริ่มต้นใช้งานเบื้องต้น (Getting Started)

1. **เตรียมไฟล์ CSV:** 
   * โปรแกรมนี้ต้องการไฟล์อินพุตแบบ `.csv` ที่มีโครงสร้างคือ คอลัมน์แรกเป็น `ID` (เช่น `ID_001`) และคอลัมน์ถัดมาเป็นข้อความภาษาอังกฤษ
2. **เปิดโปรแกรม:** 
   * ดับเบิ้ลคลิกเปิดไฟล์ `app.exe`
3. **ตั้งค่าไฟล์:** 
   * กด **Browse** เลือกไฟล์ CSV ของคุณ
   * ช่อง Output จะถูกสร้างให้โดยอัตโนมัติ (เติม `_translated` ต่อท้ายชื่อไฟล์)
4. **ตั้งค่า AI:** 
   * เลือกรุ่น **Model** ที่คุณมี API Key (เช่น `gemini-3.5-flash`, `gpt-4o`, หรือ `claude-sonnet-4.6`)
   * นำคีย์มาใส่ในช่อง **API Key**
5. **เริ่มแปล:** 
   * กดปุ่ม **Analyze & Translate** โปรแกรมจะจัดกลุ่มคำ (Batch) และส่งแปลทีละชุดให้ทันที!

---

## 🧠 2. เทคนิคระดับเซียน: การตั้งค่า System Prompt (สำคัญมาก!)

**System Prompt** คือ "คำสั่งตั้งต้น" ที่จะกำหนดพฤติกรรม นิสัย และเงื่อนไขต่างๆ ของ AI ก่อนที่มันจะแปลเกมของคุณ

ไฟล์ `system_prompt.txt` จะถูกสร้างขึ้นในโฟลเดอร์เดียวกับตัวโปรแกรม คุณสามารถเปิดไฟล์นี้ด้วย Notepad เพื่อแก้ไขคำสั่งได้เลย!

### ⚠️ กฎเหล็ก 3 ข้อที่ต้องมีใน System Prompt เสมอ:
1. **กำหนดตัวตน (Persona):** บอก AI ว่ามันเป็นใคร (เช่น เป็นนักแปลเกมระดับปรมาจารย์)
2. **รักษาตัวแปร (Preserve Variables):** สั่งห้าม AI ลบแท็กพิเศษของเกม เช่น `<font>`, `{0}`, `\n` ทิ้งเด็ดขาด
3. **บังคับรูปแบบผลลัพธ์ (Strict Output Format):** บังคับให้ AI คืนค่ากลับมาในรูปแบบ ID กั้นด้วย Tab ตามด้วยคำแปลเสมอ

### 💡 ตัวอย่าง System Prompt สำหรับเกม 3 สไตล์:

#### 🗡️ แบบที่ 1: เกม RPG / Fantasy (เช่น Skyrim, Witcher)
```text
I want you to act as a Master-Level English-to-Thai Video Game Localization Specialist.
You are translating a Dark Fantasy RPG game. 
Use appropriate Thai fantasy terminology, royal vocabulary (ราชาศัพท์) where suitable, and dramatic tone.

CRITICAL RULES:
1. PRESERVE VARIABLES: Any placeholders like [TAG_0], {0}, <font color="...">, \n, or %s MUST remain exactly intact in the translated text. Do NOT translate or remove them.
2. EXACT OUTPUT FORMAT: You will receive a list of IDs and English text. You MUST return ONLY the translated text in this exact tab-separated format, one per line:
"ID_XXXXX"	"THAI_TRANSLATION"
Do not include any other explanations.
```

#### 🚀 แบบที่ 2: เกม Sci-Fi / อวกาศ (เช่น Mass Effect, Cyberpunk)
```text
I want you to act as a Master-Level English-to-Thai Video Game Localization Specialist.
You are translating a Futuristic Sci-Fi game. 
Use modern, technical Thai terms. Keep military and scientific jargon sounding professional.

CRITICAL RULES:
1. PRESERVE VARIABLES: Any placeholders like [TAG_0], {0}, <br>, \n MUST remain exactly intact.
2. EXACT OUTPUT FORMAT: ID\tTHAI_TRANSLATION
No markdown, no extra text.
```

#### 🛋️ แบบที่ 3: เกมจำลองชีวิต / Casual (เช่น The Sims, Stardew Valley)
```text
I want you to act as a Master-Level English-to-Thai Video Game Localization Specialist.
You are translating a cozy life-simulation game. 
Use a friendly, casual, and warm Thai tone (ภาษาพูดที่เป็นธรรมชาติ).

CRITICAL RULES:
1. PRESERVE VARIABLES: Any placeholders like [TAG_0], {0}, \n MUST remain exactly intact.
2. EXACT OUTPUT FORMAT: ID\tTHAI_TRANSLATION
No markdown, no extra text.
```

---

## 📚 3. การใช้งาน Glossary & Canary Words

ในหน้าต่างโปรแกรม จะมีช่องให้ใส่ตั้งค่าพิเศษเพื่อควบคุม AI:

*   **Canary Words (คำต้องห้าม):** 
    บางครั้ง AI มักจะ "หลอน" (Hallucinate) และเติมคำแปลกๆ ที่เราไม่ได้สั่งลงไป เช่น คำว่า `[คำแปล]` หรือ `(ภาษาไทย)` 
    คุณสามารถใส่คำพวกนี้คั่นด้วยเครื่องหมายจุลภาค (,) เช่น `[คำแปล], (ภาษาไทย), AI language model` เพื่อให้โปรแกรมบล็อกไม่ให้เซฟลงไฟล์
*   **Custom Glossary (พจนานุกรมคำศัพท์):**
    หากคุณต้องการบังคับให้ AI แปลคำเฉพาะให้ตรงตามที่คุณต้องการเสมอ ให้ใส่ลงในช่องนี้แบบบรรทัดต่อบรรทัด เช่น:
    ```
    Sword=ดาบยาว
    Healing Potion=น้ำยาฟื้นพลัง
    Fireball=ลูกไฟบรรลัยกัลป์
    ```

---

## 🤖 4. การเชื่อมต่อกับ Local LLM (เช่น LM Studio, Ollama)

หากคุณมีการ์ดจอที่แรงพอและไม่อยากเสียเงินค่า API ของค่ายใหญ่ คุณสามารถรัน AI โมเดลแปลภาษาด้วยตัวเองในเครื่อง (Local LLM) และเชื่อมต่อเข้ากับ Universal Game Translator ได้ดังนี้:

1. **เลือกช่อง Model:** ให้กดเลือกเป็น `custom-local-llm`
2. **ไม่ต้องใส่ API Key:** ปล่อยช่อง API Key ว่างไว้ได้เลย (โปรแกรมจะทำการ Bypass ให้โดยอัตโนมัติ)
3. **ตั้งค่า Base URL:** 
   * หากคุณใช้ **LM Studio** ให้ใส่ `http://localhost:1234/v1/chat/completions`
   * หากคุณใช้ **Ollama** หรือตัวอื่นๆ ให้เปลี่ยน Port เลข `1234` เป็น Port ของโปรแกรมนั้นๆ
4. **ตั้งค่า Custom Model Name:** ใส่ชื่อโมเดลที่คุณโหลดมา เช่น `llama-3-8b` หรือ `qwen-2.5` เพื่อให้โปรแกรมส่งคำสั่งไปได้ถูกต้อง

เพียงเท่านี้ คุณก็สามารถแปลเกมโดยใช้พลังจากคอมพิวเตอร์ของคุณเอง 100% ปลอดภัยและฟรีแบบไร้ขีดจำกัด!

---
**Enjoy Modding! สร้างสรรค์ผลงานแปลเกมภาษาไทยระดับคุณภาพไปพร้อมกัน!**
*by NodNuatTranslator*
