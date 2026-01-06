import json
import os
import re
from difflib import get_close_matches
from typing import Dict, Optional

DATA_DIR = "data"
LANGDICT_PATH = f"{DATA_DIR}/lang_dict.json"
SUPPORTED_LANGS = ["ja", "en", "ko", "zh"]

# =========================
# ユーティリティ
# =========================
def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================
# モデル本体
# =========================
class JsonAIModel:
    """
    LangDictJsonを用いた翻訳モデル
    """
    def __init__(self):
        self.lang_dict = load_json(LANGDICT_PATH, {"entries": {}})
        self.entries = self.lang_dict.get("entries", {})

    def _normalize_text(self, text: str) -> str:
        """テキスト正規化（半角化、空白削除など）"""
        return re.sub(r"\s+", "", text.strip().lower())

    def _find_translation(self, word: str, src_lang: str, tgt_lang: str) -> Optional[str]:
        """単語・フレーズの近似検索翻訳"""
        norm_word = self._normalize_text(word)

        candidates = []
        for eid, entry in self.entries.items():
            langs = entry.get("languages", {})
            if src_lang not in langs or tgt_lang not in langs:
                continue

            src_texts = [self._normalize_text(t) for t in langs[src_lang]]
            if norm_word in src_texts:
                # 完全一致
                return langs[tgt_lang][0]

            # 類似語検索
            close = get_close_matches(norm_word, src_texts, n=1, cutoff=0.8)
            if close:
                candidates.append(langs[tgt_lang][0])

        if candidates:
            return candidates[0]
        return None

    def translate_text(
        self, text: str, src_lang: str, tgt_langs=None
    ) -> Dict[str, Optional[str]]:
        """
        文全体を翻訳。
        長文は句点で分割して個別翻訳。
        tgt_langs 指定がなければ全言語に翻訳
        """
        if tgt_langs is None:
            tgt_langs = [l for l in SUPPORTED_LANGS if l != src_lang]

        result = {lang: "" for lang in tgt_langs}
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)  # 文単位に分割

        for sentence in sentences:
            if not sentence:
                continue
            for lang in tgt_langs:
                translated = self._find_translation(sentence, src_lang, lang)
                # もし見つからなければ文をそのまま残す
                if translated is None:
                    translated = sentence
                if result[lang]:
                    result[lang] += " " + translated
                else:
                    result[lang] = translated

        return result

    def add_entry(self, entry_id: str, languages: Dict[str, list]):
        """
        新しい単語・フレーズを追加
        """
        self.entries[entry_id] = {"languages": languages}
        self.lang_dict["entries"] = self.entries
        save_json(LANGDICT_PATH, self.lang_dict)

    def update_entry_confidence(self, entry_id: str, confidence: float):
        """
        confidence更新用
        """
        if entry_id in self.entries:
            self.entries[entry_id]["confidence"] = confidence
            save_json(LANGDICT_PATH, self.lang_dict)

# =========================
# 簡単なテスト
# =========================
if __name__ == "__main__":
    model = JsonAIModel()
    src = "こんにちは"
    translations = model.translate_text(src, "ja")
    print(f"Original: {src}")
    print("Translations:", translations)