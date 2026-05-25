import os
import time
from translator_engine import TranslatorEngine

def on_log(msg):
    print("LOG:", msg)

engine = TranslatorEngine(log_callback=on_log)

config = {
    "api_key": "dummy_key",
    "model": "deepseek-chat",
    "input_csv": "test_input.csv",
    "output_csv": "test_output.csv",
    "canary_words": "",
    "glossary": "",
    "system_prompt": "Translate this."
}

with open("test_input.csv", "w", encoding="utf-8") as f:
    f.write('ID_001,"Hello World"\n')

engine.run_translation(config)
time.sleep(10)