# cogs/train_json.py

import discord
from discord.ext import commands, tasks
import json
import os
import time
from collections import defaultdict, deque
from difflib import SequenceMatcher

# =========================
# パス設定
# =========================
LOG_PATH = "data/translate_logs.json"  # translate.py が書き込むログ
LANGDICT_PATH = "data/lang_dict.json"

SUPPORTED_LANGS = ["ja", "en", "ko", "zh"]

# =========================
# ユーティリティ
# =========================
def load_json(path, default=None):
    if not os.path.exists(path):
        return default or {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def timestamp_to_date(ts):
    return time.strftime("%Y:%m:%d", time.localtime(ts))

# =========================
# 学習Cog
# =========================
class TrainJson(commands.Cog):
    """
    translate.py が出力するログをもとに LangDictJson を成長させる。
    各単語／文章に対して confidence, meaning_distance, probability を付与。
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.lang_dict = load_json(LANGDICT_PATH, {"entries": {}})
        self.context_window = 20  # 文脈履歴
        self.last_update = 0

        # 文脈ログを読み込み
        self.logs = load_json(LOG_PATH, [])

        # 非同期ループで定期更新
        self.update_task.start()

    # =========================
    # Cog終了時にタスク停止
    # =========================
    def cog_unload(self):
        self.update_task.cancel()

    # =========================
    # 定期更新タスク
    # =========================
    @tasks.loop(seconds=30.0)
    async def update_task(self):
        """
        30秒ごとにログを確認して LangDictJson を更新
        """
        self.logs = load_json(LOG_PATH, [])
        self.train_lang_dict()
        save_json(LANGDICT_PATH, self.lang_dict)

    # =========================
    # 学習ロジック
    # =========================
    def train_lang_dict(self):
        """
        ログを解析して LangDictJson を更新
        """
        entries = self.lang_dict.setdefault("entries", {})

        # チャンネル別文脈履歴
        context_logs = defaultdict(lambda: deque(maxlen=self.context_window))

        for log in self.logs:
            ts = log.get("timestamp")
            word = log.get("word", {})

            # タイムスタンプごとの文脈に格納
            context_logs[ts].append(word)

            # 各言語の単語／文章ごとに処理
            for lang, text in word.items():
                if not text:
                    continue

                # 既存エントリ検索（単語が一致するもの）
                entry_id = None
                for eid, entry in entries.items():
                    if lang in entry["languages"] and text in entry["languages"][lang]:
                        entry_id = eid
                        break

                # 新規エントリ作成
                if not entry_id:
                    new_id = str(max(map(int, entries.keys()), default=1000) + 1)
                    entries[new_id] = {
                        "languages": {lang: [text]},
                        "confidence": 0.3,
                        "meaning_distance": {},
                        "probability": {},
                        "last_modified": ts
                    }
                    entry_id = new_id

                entry = entries[entry_id]

                # confidence 更新（時間と使用回数に応じて）
                old_conf = entry.get("confidence", 0.3)
                entry["confidence"] = min(1.0, old_conf + 0.05)

                # 文脈距離を更新
                for other_ts, other_words in context_logs.items():
                    if other_ts == ts:
                        continue
                    for o_lang, o_text in other_words:
                        if o_lang == lang:
                            continue
                        # 他言語単語との距離
                        key = f"{o_lang}:{o_text}"
                        entry.setdefault("meaning_distance", {})
                        entry["meaning_distance"][key] = entry["meaning_distance"].get(key, 0.0) + 0.05

                # probability を confidence に比例して計算
                entry["probability"][lang] = entry["confidence"] / sum(
                    e.get("confidence", 0.3) for e in entries.values()
                )

                entry["last_modified"] = ts

        self.last_update = time.time()

    # =========================
    # 手動トリガー
    # =========================
    @commands.command(name="train_langdict")
    async def manual_train(self, ctx: commands.Context):
        """
        管理者が手動で LangDictJson を更新
        """
        self.logs = load_json(LOG_PATH, [])
        self.train_lang_dict()
        save_json(LANGDICT_PATH, self.lang_dict)
        await ctx.send("✅ LangDictJsonを更新しました。")

# =========================
# Cog登録
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(TrainJson(bot))