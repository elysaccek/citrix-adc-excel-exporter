import json
import os

class LanguageManager:
    def __init__(self, lang_code="TR"):
        self.lang_code = lang_code
        self.translations = {}
        self.load_language(lang_code)

    def load_language(self, lang_code):
        file_path = os.path.join(os.path.dirname(__file__), "locales", f"{lang_code}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"[!] Language file not found: {file_path}. Default language cannot be used.")
            self.translations = {}

    def get(self, key, **kwargs):
        keys = key.split('.')
        val = self.translations
        
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return key
        
        if isinstance(val, dict):
            return key
            
        if kwargs:
            try:
                return val.format(**kwargs)
            except (KeyError, AttributeError):
                return val
                
        return val

lang = LanguageManager(os.getenv("APP_LANG", "TR"))

def _(key, **kwargs):
    return lang.get(key, **kwargs)