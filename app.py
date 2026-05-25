import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from translator_engine import TranslatorEngine
import os
import json

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal Game Translator - by-NodNuatTranslator v1.0")
        self.geometry("900x700")

        self.engine = TranslatorEngine(log_callback=self.update_log, progress_callback=self.update_progress)
        self.config_file = "config.json"
        
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. File Selection Frame
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(file_frame, text="1. Select Files", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.input_file_var = tk.StringVar()
        ctk.CTkEntry(file_frame, textvariable=self.input_file_var, width=500, placeholder_text="Input CSV Path").grid(row=1, column=0, padx=10, pady=(0, 10))
        ctk.CTkButton(file_frame, text="Browse", width=100, command=self.browse_input).grid(row=1, column=1, padx=10, pady=(0, 10))
        
        self.output_file_var = tk.StringVar(value="output_translated.csv")
        ctk.CTkEntry(file_frame, textvariable=self.output_file_var, width=500, placeholder_text="Output CSV Path").grid(row=2, column=0, padx=10, pady=(0, 10))

        # 2. Settings Frame
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        ctk.CTkLabel(settings_frame, text="2. API Settings", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(settings_frame, text="API Key:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.api_key_var = tk.StringVar()
        ctk.CTkEntry(settings_frame, textvariable=self.api_key_var, width=300).grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Model:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.model_var = ctk.StringVar(value="gemini-3.5-flash")
        
        all_models = [
            # Google Gemini (2025-2026)
            "gemini-3.5-flash", "gemini-3.1-pro", "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash",
            # DeepSeek (2025-2026)
            "deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner",
            # Anthropic Claude (2025-2026)
            "claude-opus-4.7", "claude-sonnet-4.6", "claude-haiku-4.5", "claude-3-5-sonnet-20241022",
            # OpenAI
            "gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini"
        ]
        
        ctk.CTkOptionMenu(settings_frame, variable=self.model_var, values=all_models).grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # 3. Glossary Frame
        glossary_frame = ctk.CTkFrame(self)
        glossary_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        ctk.CTkLabel(glossary_frame, text="3. Glossary & Prompt", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(glossary_frame, text="Canary Words (comma separated):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.canary_var = tk.StringVar()
        ctk.CTkEntry(glossary_frame, textvariable=self.canary_var, width=350).grid(row=2, column=0, padx=10, pady=5)
        
        ctk.CTkLabel(glossary_frame, text="Custom Glossary (e.g. Sword=ดาบ):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.glossary_text = ctk.CTkTextbox(glossary_frame, width=450, height=250)
        self.glossary_text.grid(row=4, column=0, padx=10, pady=5)

        # 4. Log/Terminal Frame
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(log_frame, state="disabled", fg_color="black", text_color="lightgreen", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # 5. Action Buttons
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        
        self.start_btn = ctk.CTkButton(action_frame, text="Analyze & Translate", command=self.start_translation, width=200, height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(action_frame, text="Stop", command=self.stop_translation, fg_color="red", hover_color="darkred", width=100, height=40)
        self.stop_btn.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(action_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=20)
        self.progress_bar.set(0)

    def update_log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def update_progress(self, val):
        self.progress_bar.set(val)
        if val >= 1.0:
            self.start_btn.configure(state="normal")

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if filename:
            self.input_file_var.set(filename)
            if not self.output_file_var.get() or self.output_file_var.get() == "output_translated.csv":
                base, ext = os.path.splitext(filename)
                self.output_file_var.set(f"{base}_translated{ext}")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_data = data.get("api_settings", {})
                    self.api_key_var.set(api_data.get("api_key", ""))
                    self.model_var.set(api_data.get("model", "deepseek-chat"))
                    
                    file_data = data.get("file_settings", {})
                    self.input_file_var.set(file_data.get("input_csv", ""))
                    self.output_file_var.set(file_data.get("output_csv", "output_translated.csv"))
                    
                    safe_data = data.get("safety_settings", {})
                    self.canary_var.set(", ".join(safe_data.get("canary_words", [])))
            except:
                pass
        
        sys_prompt_file = "system_prompt.txt"
        if os.path.exists(sys_prompt_file):
            try:
                with open(sys_prompt_file, 'r', encoding='utf-8') as f:
                    self.sys_prompt_base = f.read().strip()
            except:
                self.sys_prompt_base = "I want you to act as a Master-Level English-to-Thai Video Game Localization Specialist.\n1. PRESERVE VARIABLES: Any placeholders like [TAG_0], {0}, etc. MUST remain exactly intact.\n2. EXACT OUTPUT FORMAT: ID\\tTHAI_TRANSLATION"
        else:
            self.sys_prompt_base = "I want you to act as a Master-Level English-to-Thai Video Game Localization Specialist.\n1. PRESERVE VARIABLES: Any placeholders like [TAG_0], {0}, etc. MUST remain exactly intact.\n2. EXACT OUTPUT FORMAT: ID\\tTHAI_TRANSLATION"

    def save_config(self):
        data = {
            "api_settings": {
                "api_key": self.api_key_var.get(),
                "model": self.model_var.get()
            },
            "file_settings": {
                "input_csv": self.input_file_var.get(),
                "output_csv": self.output_file_var.get()
            },
            "safety_settings": {
                "canary_words": [w.strip() for w in self.canary_var.get().split(",") if w.strip()]
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def start_translation(self):
        self.save_config()
        self.start_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.update_log("Starting Analysis & Translation...")
        
        config = {
            "api_key": self.api_key_var.get(),
            "model": self.model_var.get(),
            "input_csv": self.input_file_var.get(),
            "output_csv": self.output_file_var.get(),
            "canary_words": self.canary_var.get(),
            "glossary": self.glossary_text.get("1.0", "end-1c"),
            "system_prompt": self.sys_prompt_base
        }
        
        self.engine.run_translation(config)

    def stop_translation(self):
        self.engine.stop_translation()
        self.start_btn.configure(state="normal")

if __name__ == "__main__":
    app = TranslatorApp()
    app.mainloop()
