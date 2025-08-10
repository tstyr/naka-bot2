import discord
import random
import datetime
import os
import asyncio
import json
import math
import time

# @@@ 初期化デバッグ: このスクリプトが読み込まれ、実行を開始しました！ @@@

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Message Content Intent を有効にする
intents.reactions = True  # リアクションイベントを有効にする
bot = discord.Client(intents=intents)

USER_DATA_FILE = 'user_data.json'
BOT_SETTINGS_FILE = 'bot_settings.json'
AUTO_RNG_SESSIONS_FILE = 'auto_rng_sessions.json'
DAILY_SUMMARY_STATE_FILE = 'daily_summary_state.json'
ADMIN_IDS = [929555026612715530, 974264083853492234, 997803924281118801, 950387247985864725]

# 各アイテムの基本確率 (分母)
base_item_chances_denominator = {
    "haka": 1000000,
    "shiny haka": 3000000,
    "hage uku": 50,
    "うくうく": 2,
    "ごあ": 100000000,
    "はかうく": 4,
    "じゃうく": 10000000,
    "ピグパイセン": 1000000000,
    "みず": 30,
    "激ヤバみず": 10000000000,
    "ねこぶる": 100000,
    "pro bot": 5000
}

# 合成レシピと直接ドロップ確率を動的に生成する関数
def generate_item_data(base_chances):
    all_item_chances = {}
    crafting_recipes = {}

    for item_name, base_chance in base_chances.items():
        # 基本アイテム
        all_item_chances[item_name] = base_chance

        # Golden版
        golden_item_name = f"golden {item_name}"
        golden_chance = base_chance * 10
        all_item_chances[golden_item_name] = golden_chance

        # Rainbow版
        rainbow_item_name = f"rainbow {item_name}"
        rainbow_chance = base_chance * 100
        all_item_chances[rainbow_item_name] = rainbow_chance

        # 合成レシピ: 基本 -> Golden
        crafting_recipes[golden_item_name] = {
            "materials": {item_name: 10},
            "output": {golden_item_name: 1}
        }
        # 合成レシピ: Golden -> Rainbow
        crafting_recipes[rainbow_item_name] = {
            "materials": {golden_item_name: 10},
            "output": {rainbow_item_name: 1}
        }

    return all_item_chances, crafting_recipes

rare_item_chances_denominator, CRAFTING_RECIPES = generate_item_data(base_item_chances_denominator)

# --- Luck Potionのレシピ定義 ---

LUCK_POTION_RECIPES = {
    "rtx4070": {
        "materials": {"rainbow じゃうく": 1},
        "output": {"one_billion_luck_potion": 1},
        "luck_multiplier": 1000000000
    },
    "ねこぶるpc": {
        "materials": {"rainbow hage uku": 3, "rainbow みず": 3},
        "output": {"ten_thousand_luck_potion": 1},
        "luck_multiplier": 10000
    },
    # ★★★ ここから新しいLuck Itemを追加 ★★★
    "rtx3060": {
        "materials": {"rtx4050": 10}, # レシピを追加
        "output": {"rtx3060_luck_potion": 1}, # 内部名
        "luck_multiplier": 800000 # 80万倍
    },
    "rtx4050": {
        "materials": {"ねこぶるpc": 10}, # レシピを追加
        "output": {"rtx4050_luck_potion": 1}, # 内部名
        "luck_multiplier": 400000 # 40万倍
    },
    "rtx4060": {
        "materials": {"rtx3060": 10}, # レシピを追加
        "output": {"rtx4060_luck_potion": 1}, # 内部名
        "luck_multiplier": 5000000 # 500万倍
    },
    "rtx6000": {
        "materials": {"rtx4060": 10}, # レシピを追加
        "output": {"rtx6000_luck_potion": 1}, # 内部名
        "luck_multiplier": 10000000 # 1000万倍
    }
    # ★★★ ここまで新しいLuck Itemを追加 ★★★
}

# 内部的なポーション名と倍率のマッピング
LUCK_POTION_EFFECTS = {
    "one_billion_luck_potion": 1000000000,
    "ten_thousand_luck_potion": 10000,
    # ★★★ ここから新しいLuck Itemの内部名と倍率を追加 ★★★
    "rtx3060_luck_potion": 800000,
    "rtx4050_luck_potion": 400000,
    "rtx4060_luck_potion": 5000000,
    "rtx6000_luck_potion": 10000000
    # ★★★ ここまで新しいLuck Itemの内部名と倍率を追加 ★★★
}


auto_rng_sessions = {}
bot_settings = {}
user_data = {}

user_data_lock = asyncio.Lock()
daily_summary_state_lock = asyncio.Lock()

# --- データ保存・ロード関数 ---
def save_user_data():
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

def load_user_data():
    global user_data
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                user_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"ERROR: user_data.jsonの読み込み中にエラーが発生しました: {e}")
                print("既存のuser_data.jsonをバックアップし、新しく空のデータを作成します。")
                if os.path.exists(USER_DATA_FILE):
                    os.rename(USER_DATA_FILE, USER_DATA_FILE + ".bak." + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                user_data = {}
                save_user_data()
    else:
        user_data = {}

def save_bot_settings():
    with open(BOT_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bot_settings, f, ensure_ascii=False, indent=4)

def load_bot_settings():
    global bot_settings
    if os.path.exists(BOT_SETTINGS_FILE):
        with open(BOT_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            try:
                bot_settings = json.load(f)
            except json.JSONDecodeError as e:
                print(f"ERROR: bot_settings.jsonの読み込み中にエラーが発生しました: {e}")
                print("既存のbot_settings.jsonをバックアップし、新しく空のデータを作成します。")
                if os.path.exists(BOT_SETTINGS_FILE):
                    os.rename(BOT_SETTINGS_FILE, BOT_SETTINGS_FILE + ".bak." + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                bot_settings = {"notification_channel_id": None}
                save_bot_settings()
    else:
        bot_settings = {"notification_channel_id": None}

def save_auto_rng_sessions():
    serializable_sessions = {}
    for user_id, session_data in auto_rng_sessions.items():
        serializable_sessions[user_id] = {
            "found_items_log": session_data["found_items_log"],
            "start_time": session_data["start_time"].timestamp(),
            "max_duration_seconds": session_data["max_duration_seconds"]
        }
    with open(AUTO_RNG_SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_sessions, f, ensure_ascii=False, indent=4)
    print("オートRNGセッションデータを保存しました。")

def load_auto_rng_sessions():
    global auto_rng_sessions
    if os.path.exists(AUTO_RNG_SESSIONS_FILE):
        with open(AUTO_RNG_SESSIONS_FILE, 'r', encoding='utf-8') as f:
            try:
                loaded_sessions = json.load(f)
                auto_rng_sessions = {}
                for user_id, session_data in loaded_sessions.items():
                    auto_rng_sessions[user_id] = {
                        "task": None,
                        "found_items_log": session_data["found_items_log"],
                        "start_time": datetime.datetime.fromtimestamp(session_data["start_time"], tz=datetime.timezone.utc),
                        "max_duration_seconds": session_data["max_duration_seconds"]
                    }
                print("オートRNGセッションデータをロードしました。")
            except json.JSONDecodeError as e:
                print(f"ERROR: auto_rng_sessions.jsonの読み込み中にエラーが発生しました: {e}")
                print("既存のauto_rng_sessions.jsonをバックアップし、新しく空のデータを作成します。")
                if os.path.exists(AUTO_RNG_SESSIONS_FILE):
                    os.rename(AUTO_RNG_SESSIONS_FILE, AUTO_RNG_SESSIONS_FILE + ".bak." + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                auto_rng_sessions = {}
                save_auto_rng_sessions()
    else:
        auto_rng_sessions = {}
        print("オートRNGセッションデータファイルが見つかりませんでした。")

def load_daily_summary_state_main():
    state = {
        "last_processed_date": None,
        "rolls_since_last_processed": 0,
        "most_rare_item_today_info": {
            "item_name": None,
            "original_denominator": 0,
            "finder_id": None,
            "timestamp": None
        }
    }
    if os.path.exists(DAILY_SUMMARY_STATE_FILE):
        with open(DAILY_SUMMARY_STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                loaded_state = json.load(f)
                state["last_processed_date"] = loaded_state.get("last_processed_date")
                state["rolls_since_last_processed"] = loaded_state.get("rolls_since_last_processed", 0)
                state["most_rare_item_today_info"] = loaded_state.get("most_rare_item_today_info", {
                    "item_name": None, "original_denominator": 0, "finder_id": None, "timestamp": None
                })
            except json.JSONDecodeError as e:
                print(f"ERROR: {DAILY_SUMMARY_STATE_FILE} の読み込み中にエラーが発生しました (main): {e}")
    return state

def save_daily_summary_state_main(state_to_save):
    with open(DAILY_SUMMARY_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state_to_save, f, ensure_ascii=False, indent=4)

# --- Botのステータスを更新する非同期タスク ---
async def update_total_rolls_status():
    await bot.wait_until_ready()

    while not bot.is_closed():
        total_rolls = 0
        async with user_data_lock:
            for user_id in user_data:
                total_rolls += user_data[user_id].get("rolls", 0)

        activity_name = f"{total_rolls:,} 回のロール！"
        await bot.change_presence(activity=discord.Game(name=activity_name))
        print(f"Updated bot status to: {activity_name}")

        await asyncio.sleep(20)

# --- イベントハンドラ ---
@bot.event
async def on_ready():
    print(f'ログイン完了: {bot.user}')
    load_user_data()
    load_bot_settings()
    load_auto_rng_sessions()

    print("ユーザーデータをロードしました。")
    print("ボット設定をロードしました。")

    current_time_utc = datetime.datetime.now(datetime.timezone.utc)
    sessions_to_restart = []
    for user_id in list(auto_rng_sessions.keys()):
        session_data = auto_rng_sessions[user_id]
        elapsed_time = (current_time_utc - session_data["start_time"]).total_seconds()
        remaining_time = session_data["max_duration_seconds"] - elapsed_time

        if remaining_time > 0:
            sessions_to_restart.append(user_id)
        else:
            del auto_rng_sessions[user_id]
            save_auto_rng_sessions()

    for user_id in sessions_to_restart:
        try:
            user = await bot.fetch_user(int(user_id))
            auto_rng_sessions[user_id]["task"] = bot.loop.create_task(auto_roll_task(user, is_resumed=True))
            print(f"User {user.name} ({user_id}) のオートRNGセッションを再開しました。")
        except discord.NotFound:
            print(f"警告: ユーザーID {user_id} が見つからないため、オートRNGセッションを再開できませんでした。セッションを削除します。")
            if user_id in auto_rng_sessions:
                del auto_rng_sessions[user_id]
            save_auto_rng_sessions()
        except Exception as e:
            print(f"ERROR: オートRNGセッション再開中にエラーが発生しました (ユーザーID: {user_id}): {e}")

    bot.loop.create_task(update_total_rolls_status())

async def send_auto_rng_results(user: discord.User, found_items_log: dict, total_rolls: int, stop_reason: str):
    """オートRNGの結果をユーザーにDMで送信する"""
    if not found_items_log:
        await user.send(f"オートRNGが**{stop_reason}**しました。残念ながら何も見つかりませんでした。総ロール数: **{total_rolls}**回")
        return

    result_text = f"オートRNGが**{stop_reason}**しました！\n\n**今回見つかったアイテム:**\n"

    for item, count in found_items_log.items():
        result_text += f"- {item}: {count}個\n"

    result_text += f"\n**総ロール数:** {total_rolls}回"

    if len(result_text) > 2000:
        chunks = [result_text[i:i + 1900] for i in range(0, len(result_text), 1900)]
        for chunk in chunks:
            await user.send(chunk)
    else:
        await user.send(result_text)

# --- ロール実行ロジックの共通化 ---
def perform_roll(luck, user_id):
    """
    アイテムを抽選し、結果を返す。
    必ず何かしらのアイテムがドロップするように保証する。
    Luckが高いほど、分母が小さくなる（出やすくなる）が、コモンアイテムには限定的な効果。
    """
    items = list(rare_item_chances_denominator.keys())

    effective_probabilities = {}
    for item in items:
        original_denominator = rare_item_chances_denominator[item]

        if original_denominator <= 50:
            luck_factor = 1.0
            if luck > 1:
                luck_factor = luck ** 0.1
            elif luck < 1:
                luck_factor = luck
            effective_denominator = original_denominator / luck_factor
        else:
            effective_denominator = original_denominator / luck
            effective_denominator = max(0.0000000001, effective_denominator)

        effective_probabilities[item] = 1.0 / effective_denominator
        if effective_probabilities[item] > 1.0:
            effective_probabilities[item] = 1.0

    weights = list(effective_probabilities.values())
    if sum(weights) == 0:
        weights = [1.0] * len(items)

    chosen_item = random.choices(items, weights=weights, k=1)[0]

    display_denominator_for_roll = 1.0 / effective_probabilities[chosen_item]
    if display_denominator_for_roll < 1.0:
        display_denominator_for_roll = 1
    else:
        display_denominator_for_roll = math.floor(display_denominator_for_roll)

    original_denominator = rare_item_chances_denominator[chosen_item]

    return chosen_item, display_denominator_for_roll, original_denominator

# --- ページネーション用グローバル辞書 ---
pagination_sessions = {}

async def generate_itemlist_embed(user_id, page_num, items_per_page, category_name, category_items, total_item_counts):
    user_inventory = user_data[str(user_id)]["inventory"]

    print(f"DEBUG: generate_itemlist_embed: user_inventory retrieved. User ID: {user_id}")

    start_index = page_num * items_per_page
    end_index = start_index + items_per_page
    items_to_display = category_items[start_index:end_index]
    print(f"DEBUG: generate_itemlist_embed: Items to display count: {len(items_to_display)}")

    total_pages = math.ceil(len(category_items) / items_per_page)
    if total_pages == 0:
        total_pages = 1
    print(f"DEBUG: generate_itemlist_embed: Total pages: {total_pages}, Current page: {page_num}")

    embed_title = ""
    if category_name == "normal":
        embed_title = f"ノーマルアイテムリスト (ページ {page_num + 1}/{total_pages})"
    elif category_name == "golden":
        embed_title = f"ゴールデンアイテムリスト (ページ {page_num + 1}/{total_pages})"
    elif category_name == "rainbow":
        embed_title = f"レインボーアイテムリスト (ページ {page_num + 1}/{total_pages})"
    print(f"DEBUG: generate_itemlist_embed: Embed title: {embed_title}")

    embed = discord.Embed(
        title=embed_title,
        description="全アイテムの確率とあなたの所持数、そしてサーバー全体の総所持数です。",
        color=discord.Color.orange()
    )

    if not items_to_display:
        print("DEBUG: generate_itemlist_embed: No items to display in this category.")
        embed.add_field(name="情報なし", value="このカテゴリにはアイテムがありません。", inline=False)
    else:
        for item_name, chance_denominator in items_to_display:
            display_chance = f"1 in {chance_denominator:,}"
            owned_count = user_inventory.get(item_name, 0)
            total_owned_count = total_item_counts.get(item_name, 0)
            embed.add_field(name=item_name, value=f"確率: {display_chance}\nあなたの所持数: {owned_count}個\nサーバー総所持数: {total_owned_count}個", inline=True)
            print(f"DEBUG: generate_itemlist_embed: Added field for item: {item_name}")

    embed.set_footer(text=f"ページ {page_num + 1}/{total_pages} | レアリティ順")
    print("DEBUG: generate_itemlist_embed: Embed footer set. Returning embed.")
    return embed

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if reaction.message.id in pagination_sessions:
        session = pagination_sessions[reaction.message.id]

        if user.id != int(session["user_id"]):
            await reaction.remove(user)
            return

        current_page = session["current_page"]
        items_per_page = session["items_per_page"]
        current_category = session["current_category"]
        total_item_counts = session["total_item_counts"]

        category_items_map = {
            "normal": session["normal_items"],
            "golden": session["golden_items"],
            "rainbow": session["rainbow_items"]
        }
        category_items = category_items_map.get(current_category, [])

        max_pages = math.ceil(len(category_items) / items_per_page)
        if max_pages == 0:
            max_pages = 1

        new_page = current_page
        new_category = current_category

        if str(reaction.emoji) == '🐾':
            new_category = "normal"
            new_page = 0
        elif str(reaction.emoji) == '⭐':
            new_category = "golden"
            new_page = 0
        elif str(reaction.emoji) == '🌈':
            new_category = "rainbow"
            new_page = 0
        elif str(reaction.emoji) == '◀️':
            new_page = max(0, current_page - 1)
        elif str(reaction.emoji) == '▶️':
            new_page = min(max_pages - 1, current_page + 1)

        if new_category != current_category or new_page != current_page:
            session["current_page"] = new_page
            session["current_category"] = new_category

            updated_category_items = category_items_map.get(new_category, [])

            updated_max_pages = math.ceil(len(updated_category_items) / items_per_page)
            if updated_max_pages == 0:
                updated_max_pages = 1

            if new_page >= updated_max_pages:
                session["current_page"] = 0

            updated_embed = await generate_itemlist_embed(
                session["user_id"],
                session["current_page"],
                session["items_per_page"],
                session["current_category"],
                updated_category_items,
                total_item_counts
            )
            await reaction.message.edit(embed=updated_embed)
            await reaction.remove(user)
        else:
            await reaction.remove(user)

@bot.event
async def on_message(message):
    print(f"DEBUG: on_message called! Author: {message.author.name}, Content: '{message.content}'")
    print(f"DEBUG: Raw message content (type/len): {type(message.content)}, {len(message.content)}")
    print(f"DEBUG: Raw message content (unicode codepoints): {[ord(c) for c in message.content]}")

    global user_data
    global auto_rng_sessions
    if message.author.bot:
        if message.author.name == "UnbelievaBoat" and message.content.strip() == "":
            print(f"DEBUG: Ignoring empty message from bot: {message.author.name}")
            return
        print(f"DEBUG: Ignoring message from another bot: {message.author.name} (Content: '{message.content}')")
        return

    user_id = str(message.author.id)
    command_content = message.content.lower().strip()
    print(f"DEBUG: Processed command_content: '{command_content}' (Length: {len(command_content)})")
    print(f"DEBUG: Processed command_content (unicode codepoints): {[ord(c) for c in command_content]}")

    try:
        async with user_data_lock:
            if user_id not in user_data:
                print(f"DEBUG: Initializing user data for {user_id}")
                user_data[user_id] = {
                    "rolls": 0,
                    "luck": 1.0,
                    "inventory": {},
                    "luck_potions": {},
                    "active_luck_potion_uses": {},
                    "daily_login": {
                        "last_login_date": None,
                        "consecutive_days": 0,
                        "active_boost": {
                            "multiplier": 1.0,
                            "end_time": None
                        }
                    },
                    "admin_boost": {
                        "multiplier": 1.0,
                        "end_time": None
                    }
                }
                save_user_data()

            if "daily_login" not in user_data[user_id]:
                print(f"DEBUG: Adding 'daily_login' to user data for {user_id}")
                user_data[user_id]["daily_login"] = {
                    "last_login_date": None,
                    "consecutive_days": 0,
                    "active_boost": {
                        "multiplier": 1.0,
                        "end_time": None
                    }
                }
                save_user_data()

            if "luck_potions" not in user_data[user_id]:
                print(f"DEBUG: Adding 'luck_potions' to user data for {user_id}")
                user_data[user_id]["luck_potions"] = {}
                save_user_data()

            if "active_luck_potion_uses" not in user_data[user_id]:
                print(f"DEBUG: Adding 'active_luck_potion_uses' to user data for {user_id}")
                user_data[user_id]["active_luck_potion_uses"] = {}
                save_user_data()

            if "admin_boost" not in user_data[user_id]:
                print(f"DEBUG: Adding 'admin_boost' to existing user data for {user_id}")
                user_data[user_id]["admin_boost"] = {
                    "multiplier": 1.0,
                    "end_time": None
                }
                save_user_data()

        current_time_on_message = datetime.datetime.now(datetime.timezone.utc)
        
        async with user_data_lock:
            user_boost = user_data[user_id]["daily_login"]["active_boost"]

            if user_boost["end_time"] and current_time_on_message > datetime.datetime.fromtimestamp(user_boost["end_time"], tz=datetime.timezone.utc):
                user_boost["multiplier"] = 1.0
                user_boost["end_time"] = None
                save_user_data()
                try:
                    await message.channel.send(f"{message.author.mention} の一時的なラックブーストが終了しました。")
                except Exception as e:
                    print(f"WARNING: Could not send daily boost expired message for {message.author.name}: {e}")
            
            admin_boost_info = user_data[user_id].get("admin_boost", {"multiplier": 1.0, "end_time": None})
            if admin_boost_info["end_time"] and current_time_on_message > datetime.datetime.fromtimestamp(admin_boost_info["end_time"], tz=datetime.timezone.utc):
                user_data[user_id]["luck"] = 1.0
                user_data[user_id]["admin_boost"]["multiplier"] = 1.0
                user_data[user_id]["admin_boost"]["end_time"] = None
                save_user_data()
                try:
                    await message.channel.send(f"{message.author.mention} の管理者ラックブーストが終了し、元のラックに戻りました。")
                except Exception as e:
                    print(f"WARNING: Could not send admin boost expired message for {message.author.name}: {e}")

            user_luck = user_data[user_id]["luck"]

        if command_content == "!help":
            print("DEBUG: Entering !help command block.")
            try:
                embed = discord.Embed(
                    title="コマンド一覧",
                    description="このボットで使えるコマンドはこちらです。",
                    color=discord.Color.green()
                )
                embed.add_field(name="**!rng**", value="ランダムアイテムをロールします。", inline=False)
                embed.add_field(name="**!status**", value="あなたの現在のロール数、ラック、インベントリを表示します。", inline=False)
                embed.add_field(name="**!itemlist**", value="全アイテムの確率とあなたの所持数、そしてサーバー全体の総所持数を表示します。", inline=False)
                embed.add_field(name="**!ranking**", value="ロール数のトッププレイヤーを表示します。", inline=False)
                embed.add_field(name="**!autorng**", value="6時間、1秒に1回自動でロールします。結果は終了後にDMで送られます。", inline=False)
                embed.add_field(name="**!autostop**", value="実行中のオートRNGを停止し、現在の結果をDMで送られます。", inline=False)
                embed.add_field(name="**!autorngtime**", value="実行中のオートRNGの残り時間を表示します。", inline=False)
                embed.add_field(name="**!ping**", value="ボットの応答速度を測定します。", inline=False)
                embed.add_field(name="**!setup**", value="高確率アイテムの通知チャンネルを設定します。", inline=False)
                embed.add_field(name="**!login**", value="デイリーログインボーナスを獲得します。連続ログインでラックブーストが向上します。", inline=False)
                embed.add_field(name="**!craft [合成したいアイテム名] [個数/all]**", value="素材を消費してよりレアなアイテムを合成します。例: `!craft golden haka 5` または `!craft golden haka all`", inline=False)
                embed.add_field(name="**!make [作成したいポーション名] [個数/all]**", value="素材を消費してLuck Potionを生成します。例: `!make rtx4070 1`", inline=False)
                embed.add_field(name="**!use [使用したいポーション名] [個数/all]**", value="Luck Potionを使用キューに追加し、次のロールから効果を適用します。例: `!use rtx4070 1`", inline=False)
                embed.add_field(name="**!recipe**", value="Luck Potionの作成レシピを表示します。", inline=False)

                print("DEBUG: Attempting to send !help embed.")
                await message.channel.send(embed=embed)
                print("DEBUG: !help embed sent.")
            except Exception as e:
                print(f"ERROR: Failed to send !help embed or during processing: {e}")
                import traceback
                traceback.print_exc()
            return

        elif command_content == "!adminhelp":
            print("DEBUG: Entering !adminhelp command block.")
            if message.author.id not in ADMIN_IDS:
                await message.channel.send("このコマンドは管理者のみが使用できます。")
                return
            try:
                embed = discord.Embed(
                    title="管理者コマンド一覧",
                    description="管理者のみが使用できるコマンドはこちらです。",
                    color=discord.Color.red()
                )
                embed.add_field(name="**!boostluck [倍率] [秒数]**", value="全員のLuckを一時的に指定倍率にします。例: `!boostluck 1.5 60` (1.5倍、60秒)", inline=False)
                embed.add_field(name="**!giveluckitem [ポーション名] [ユーザーメンションまたはID] [個数]**", value="指定したユーザーにLuck Potionを与えます。例: `!giveluckitem rtx4070 @ユーザー名 1`", inline=False)
                embed.add_field(name="**!resetall**", value="**警告: 全ユーザーのデータ（ロール数、ラック、インベントリ）をリセットします。**", inline=False)
                embed.add_field(name="**!adminautorng**", value="現在実行中の全ユーザーのオートRNG状況を表示します。", inline=False)
                embed.add_field(name="**!giveautorng [user mention or ID / all]**", value="指定したユーザーまたは全員のオートRNGを開始します。例: `!giveautorng @ユーザー名`, `!giveautorng 123456789012345678`, `!giveautorng all`", inline=False)
                embed.add_field(name="**!delete [user mention or ID / all]**", value="指定したユーザーまたは全員のデータを削除します。**回復不能な操作です！**", inline=False)
                print("DEBUG: Attempting to send !adminhelp embed.")
                await message.channel.send(embed=embed)
                print("DEBUG: !adminhelp embed sent.")
            except Exception as e:
                print(f"ERROR: Failed to send !adminhelp embed or during processing: {e}")
                import traceback
                traceback.print_exc()
            return

        elif command_content == "!ping":
            print("DEBUG: Entering !ping command block.")
            try:
                start_time = time.time()
                latency = bot.latency * 1000

                msg = await message.channel.send("Pingを測定中...")
                end_time = time.time()
                api_latency = (end_time - start_time) * 1000

                embed = discord.Embed(
                    title="Ping結果",
                    description=f"WebSocket Latency: `{latency:.2f}ms`\nAPI Latency: `{api_latency:.2f}ms`",
                    color=discord.Color.blue()
                )
                print("DEBUG: Attempting to edit Ping message with embed.")
                await msg.edit(content="", embed=embed)
                print("DEBUG: Ping message edited.")
            except Exception as e:
                print(f"ERROR: Failed to send/edit !ping message or during processing: {e}")
                import traceback
                traceback.print_exc()
            return

        elif command_content == "!setup":
            print("DEBUG: Entering !setup command block.")
            if message.author.id not in ADMIN_IDS:
                await message.channel.send("このコマンドは管理者のみが使用できます。")
                return
            try:
                bot_settings["notification_channel_id"] = message.channel.id
                save_bot_settings()
                print("DEBUG: Attempting to send !setup confirmation message.")
                await message.channel.send(f"このチャンネル（`#{message.channel.name}`）を高確率アイテムの通知チャンネルに設定しました。")
                print("DEBUG: !setup confirmation message sent.")
            except Exception as e:
                print(f"ERROR: Failed to send !setup confirmation message or during processing: {e}")
                import traceback
                traceback.print_exc()
            return

        elif command_content == "!login":
            print("DEBUG: Entering !login command block.")
            try:
                today_utc = datetime.datetime.now(datetime.timezone.utc).date()
                async with user_data_lock:
                    user_daily_data = user_data[user_id]["daily_login"]
                    last_login_date_str = user_daily_data["last_login_date"]

                    last_login_date_obj = None
                    if last_login_date_str:
                        last_login_date_obj = datetime.datetime.strptime(last_login_date_str, "%Y-%m-%d").date()

                    if last_login_date_obj == today_utc:
                        await message.channel.send("すでに今日のデイリーログイン報酬は受け取り済みです。")
                        return

                    is_consecutive = False
                    if last_login_date_obj:
                        if last_login_date_obj == today_utc - datetime.timedelta(days=1):
                            user_daily_data["consecutive_days"] += 1
                            is_consecutive = True
                        else:
                            user_daily_data["consecutive_days"] = 1
                    else:
                        user_daily_data["consecutive_days"] = 1

                    user_daily_data["last_login_date"] = today_utc.strftime("%Y-%m-%d")

                    consecutive_days = user_daily_data["consecutive_days"]

                    boost_multiplier = 1.0 + (consecutive_days * 0.1)
                    boost_duration_minutes = 5 + (consecutive_days - 1) * 1

                    max_boost_multiplier = 2.0
                    max_boost_duration_minutes = 15

                    boost_multiplier = min(boost_multiplier, max_boost_multiplier)
                    boost_duration_minutes = min(boost_duration_minutes, max_boost_duration_minutes)

                    boost_duration_seconds = boost_duration_minutes * 60
                    boost_end_time = current_time_on_message + datetime.timedelta(seconds=boost_duration_seconds)

                    user_daily_data["active_boost"]["multiplier"] = boost_multiplier
                    user_daily_data["active_boost"]["end_time"] = boost_end_time.timestamp()

                    display_luck = 1.0 * boost_multiplier

                    save_user_data()

                status_message = ""
                if is_consecutive:
                    status_message = f"**連続ログイン{consecutive_days}日目！**"
                else:
                    status_message = f"**デイリーログイン成功！**"

                print("DEBUG: Attempting to send !login confirmation message.")
                await message.channel.send(
                    f"{message.author.mention} {status_message}\n"
                    f"ラックが一時的に **{boost_multiplier:.1f}倍** になりました！ ({boost_duration_minutes}分間有効)\n"
                    f"現在のラック: **{display_luck:.1f}** (基本ラック x デイリーログインブースト)"
                )
                print("DEBUG: !login confirmation message sent.")
            except Exception as e:
                print(f"ERROR: Failed to send !login message or during processing: {e}")
                import traceback
                traceback.print_exc()
            return

        elif command_content == "!rng":
            print("DEBUG: Entering !rng command block.")
            try:
                async with user_data_lock:
                    current_base_luck = user_data[user_id]["luck"]

                    user_boost = user_data[user_id]["daily_login"]["active_boost"]
                    if user_boost["end_time"] and datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromtimestamp(user_boost["end_time"], tz=datetime.timezone.utc):
                        current_base_luck *= user_boost["multiplier"]

                    admin_boost_info = user_data[user_id].get("admin_boost", {"multiplier": 1.0, "end_time": None})
                    if admin_boost_info["end_time"] and current_time_on_message < datetime.datetime.fromtimestamp(admin_boost_info["end_time"], tz=datetime.timezone.utc):
                        current_base_luck *= admin_boost_info["multiplier"]

                    applied_potion_multiplier = 1.0
                    applied_potion_display_name = None

                    active_uses = user_data[user_id]["active_luck_potion_uses"]

                    highest_multiplier = 1.0
                    best_potion_internal_name = None

                    sorted_potions_by_multiplier = sorted(LUCK_POTION_EFFECTS.items(), key=lambda item: item[1], reverse=True)

                    for internal_name, multiplier_value in sorted_potions_by_multiplier:
                        if active_uses.get(internal_name, 0) > 0:
                            highest_multiplier = multiplier_value
                            best_potion_internal_name = internal_name
                            break

                    if best_potion_internal_name:
                        applied_potion_multiplier = highest_multiplier
                        current_luck_for_roll = current_base_luck * applied_potion_multiplier

                        active_uses[best_potion_internal_name] -= 1
                        if active_uses[best_potion_internal_name] <= 0:
                            del active_uses[best_potion_internal_name]

                        for recipe_name, recipe_data in LUCK_POTION_RECIPES.items():
                            if list(recipe_data["output"].keys())[0] == best_potion_internal_name:
                                applied_potion_display_name = recipe_name
                                break

                        print(f"DEBUG: {message.author.mention} used {applied_potion_display_name}.")
                        await message.channel.send(f"{message.author.mention} は **{applied_potion_display_name}** を使用しました！今回のロールのラックは **{current_luck_for_roll:.1f}倍** になります！")
                    else:
                        current_luck_for_roll = current_base_luck

                    user_data[user_id]["rolls"] += 1
                    user_rolls = user_data[user_id]["rolls"]
                    today = datetime.datetime.now().strftime("%B %d, %Y")

                    chosen_item, luck_applied_denominator, original_denominator = perform_roll(current_luck_for_roll, user_id)
                    display_chance_for_user = f"1 in {original_denominator:,}"

                    inventory = user_data[user_id]["inventory"]
                    inventory[chosen_item] = inventory.get(chosen_item, 0) + 1

                    embed = discord.Embed(
                        title=f"{message.author.name} が {chosen_item} を見つけました!!!",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="Chance", value=display_chance_for_user, inline=False)
                    embed.add_field(name="獲得日", value=today, inline=False)
                    embed.add_field(name="総ロール数", value=f"{user_rolls} 回", inline=False)
                    embed.add_field(name="あなたの合計ラック (ポーション適用後)", value=f"{current_luck_for_roll:.1f} Luck", inline=False)
                    
                    print("DEBUG: Attempting to send !rng embed.")
                    await message.channel.send(embed=embed)
                    print("DEBUG: !rng embed sent.")

                    save_user_data()

                async with daily_summary_state_lock:
                    current_daily_state = load_daily_summary_state_main()
                    current_most_rare_info = current_daily_state["most_rare_item_today_info"]

                    if original_denominator > current_most_rare_info["original_denominator"]:
                        current_daily_state["most_rare_item_today_info"] = {
                            "item_name": chosen_item,
                            "original_denominator": original_denominator,
                            "finder_id": user_id,
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp()
                        }
                        save_daily_summary_state_main(current_daily_state)
                        print(f"INFO: Daily most rare item updated for !rng: {chosen_item} by {user_id}")

                if original_denominator >= 100000:
                    notification_channel_id = bot_settings.get("notification_channel_id")
                    if notification_channel_id:
                        notification_channel = bot.get_channel(notification_channel_id)
                        if notification_channel:
                            total_item_counts = {item: 0 for item in rare_item_chances_denominator.keys()}
                            for uid in user_data:
                                for item, count in user_data[uid]["inventory"].items():
                                    if item in total_item_counts:
                                        total_item_counts[item] += count

                            total_owned_count = total_item_counts.get(chosen_item, 0)

                            notification_embed = discord.Embed(
                                title="レアアイテムドロップ通知！",
                                description=f"{message.author.mention} がレアアイテムを獲得しました！",
                                color=discord.Color.gold()
                            )
                            notification_embed.add_field(name="獲得者", value=message.author.mention, inline=False)
                            notification_embed.add_field(name="アイテム", value=chosen_item, inline=False)
                            notification_embed.add_field(name="確率", value=f"1 in {original_denominator:,}", inline=False)
                            notification_embed.add_field(name="獲得日時", value=datetime.datetime.now(datetime.timezone.utc).strftime("%Y年%m月%d日 %H:%M:%S UTC"), inline=False)
                            notification_embed.add_field(name="サーバー総所持数", value=f"{total_owned_count}個", inline=False)
                            notification_embed.set_footer(text="おめでとうございます！")
                            print("DEBUG: Attempting to send notification embed.")
                            await notification_channel.send(embed=notification_embed)
                            print("DEBUG: Notification embed sent.")
                        else:
                            print(f"WARNING: Configured notification channel ID {notification_channel_id} not found.")
            except Exception as e:
                print(f"ERROR: Failed to process !rng command or send embed: {e}")
                import traceback
                traceback.print_exc()
        elif command_content == "!status":
            print(f"DEBUG: Entering !status command block for user: {user_id}")
            try:
                async with user_data_lock:
                    print(f"DEBUG: user_data content for {user_id}: {user_data.get(user_id)}")
                    data = user_data[user_id]
                    
                    inventory_items_with_chances = []
                    for item_name, count in data["inventory"].items():
                        if item_name in rare_item_chances_denominator:
                            chance = rare_item_chances_denominator[item_name]
                            inventory_items_with_chances.append((item_name, count, chance))
                        else:
                            print(f"WARNING: Item '{item_name}' not found in rare_item_chances_denominator. Skipping for status display.")
                            inventory_items_with_chances.append((item_name, count, 0))

                    inventory_items_with_chances.sort(key=lambda x: x[2], reverse=True)

                    inventory_str_lines = []
                    for item_name, count, chance in inventory_items_with_chances:
                        if chance > 0:
                            inventory_str_lines.append(f"{item_name}: {count}個 (1 in {chance:,})")
                        else:
                            inventory_str_lines.append(f"{item_name}: {count}個 (確率不明)")

                    inventory_str = "\n".join(inventory_str_lines) or "なし"

                    luck_potions_str = ""
                    if data["luck_potions"]:
                        for potion_internal_name, count in data["luck_potions"].items():
                            display_name = ""
                            # Luck Potionのレシピを逆引きして表示名を取得
                            for recipe_name, recipe_data in LUCK_POTION_RECIPES.items():
                                if isinstance(recipe_data["output"], dict) and list(recipe_data["output"].keys())[0] == potion_internal_name:
                                    display_name = recipe_name
                                    break
                            if display_name:
                                # デバッグ用に内部名も表示
                                luck_potions_str += f"- {display_name} (`{potion_internal_name}`): {count}個\n"
                            else:
                                # レシピにない未知のポーションの場合も表示
                                luck_potions_str += f"- 未知のポーション (`{potion_internal_name}`): {count}個\n"
                        if not luck_potions_str:
                            luck_potions_str = "なし"
                    else:
                        luck_potions_str = "なし"

                    active_potions_str = ""
                    if data["active_luck_potion_uses"]:
                        for internal_name, count in data["active_luck_potion_uses"].items():
                            display_name = ""
                            for recipe_name, recipe_data in LUCK_POTION_RECIPES.items():
                                if isinstance(recipe_data["output"], dict) and list(recipe_data["output"].keys())[0] == internal_name:
                                    display_name = recipe_name
                                    break
                            if display_name:
                                active_potions_str += f"- {display_name}: 残り{count}回\n"
                            else: # ここも未知のポーションの場合の表示を追加
                                active_potions_str += f"- 未知のポーション (`{internal_name}`): 残り{count}回\n"
                        if not active_potions_str:
                            active_potions_str = "なし"
                    else:
                        active_potions_str = "なし"

                    boost_info = data["daily_login"]["active_boost"]
                    boost_status = "なし"
                    current_luck_for_display = data["luck"]
                    if boost_info["end_time"]:
                        end_dt = datetime.datetime.fromtimestamp(boost_info["end_time"], tz=datetime.timezone.utc)
                        remaining_time = end_dt - datetime.datetime.now(datetime.timezone.utc)
                        if remaining_time.total_seconds() > 0:
                            hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
                            minutes, seconds = divmod(remainder, 60)
                            boost_status = f"**{boost_info['multiplier']:.1f}倍** (残り {hours}h {minutes}m {seconds}s)"
                            current_luck_for_display *= boost_info["multiplier"]
                        else:
                            boost_status = "期限切れ"
                    
                    admin_boost_info = data["admin_boost"]
                    admin_boost_status = "なし"
                    if admin_boost_info["end_time"]:
                        admin_end_dt = datetime.datetime.fromtimestamp(admin_boost_info["end_time"], tz=datetime.timezone.utc)
                        admin_remaining_time = admin_end_dt - datetime.datetime.now(datetime.timezone.utc)
                        if admin_remaining_time.total_seconds() > 0:
                            admin_hours, admin_remainder = divmod(int(admin_remaining_time.total_seconds()), 3600)
                            admin_minutes, admin_seconds = divmod(admin_remainder, 60)
                            admin_boost_status = f"**{admin_boost_info['multiplier']:.1f}倍** (残り {admin_hours}h {admin_minutes}m {admin_seconds}s)"
                            current_luck_for_display *= admin_boost_info["multiplier"]
                        else:
                            admin_boost_status = "期限切れ"

                    embed = discord.Embed(
                        title=f"{message.author.name} のステータス",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="**総ロール数**", value=f"{data['rolls']}", inline=False)
                    embed.add_field(name="**ラック**", value=f"{current_luck_for_display:.1f}", inline=False)
                    embed.add_field(name="**連続ログイン日数**", value=f"{data['daily_login']['consecutive_days']}日", inline=False)
                    embed.add_field(name="**現在のログインブースト**", value=boost_status, inline=False)
                    embed.add_field(name="**現在の管理者ブースト**", value=admin_boost_status, inline=False)
                    embed.add_field(name="**アイテムインベントリ**", value=inventory_str, inline=False)
                    embed.add_field(name="**Luck Potionインベントリ**", value=luck_potions_str, inline=False)
                    embed.add_field(name="**使用待ちLuck Potion**", value=active_potions_str, inline=False)
                    
                    print("DEBUG: Attempting to send !status embed.")
                    await message.channel.send(embed=embed)
                    print("DEBUG: !status embed sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !status command or send embed: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!itemlist":
            print(f"DEBUG: Entering !itemlist command block for user: {user_id}")
            try:
                print(f"DEBUG: user_data content for {user_id}: {user_data.get(user_id)}")
                if not isinstance(user_data.get(user_id), dict) or "inventory" not in user_data[user_id]:
                    print(f"ERROR: User data for {user_id} is malformed or missing 'inventory' key. Data: {user_data.get(user_id)}")
                    await message.channel.send("ユーザーデータに問題があるため、アイテムリストを表示できませんでした。")
                    return

                user_inventory = user_data[user_id]["inventory"]

                total_item_counts = {item: 0 for item in rare_item_chances_denominator.keys()}
                async with user_data_lock:
                    for uid in user_data:
                        if isinstance(user_data[uid], dict) and "inventory" in user_data[uid]:
                            for item, count in user_data[uid]["inventory"].items():
                                if item in total_item_counts:
                                    total_item_counts[item] += count

                normal_items = []
                golden_items = []
                rainbow_items = []

                for item_name, chance_denominator in rare_item_chances_denominator.items():
                    if item_name.startswith("golden "):
                        golden_items.append((item_name, chance_denominator))
                    elif item_name.startswith("rainbow "):
                        rainbow_items.append((item_name, chance_denominator))
                    else:
                        normal_items.append((item_name, chance_denominator))

                normal_items.sort(key=lambda item: item[1], reverse=True)
                golden_items.sort(key=lambda item: item[1], reverse=True)
                rainbow_items.sort(key=lambda item: item[1], reverse=True)

                items_per_page = 10

                print("DEBUG: Calling generate_itemlist_embed.")
                initial_embed = await generate_itemlist_embed(user_id, 0, items_per_page, "normal", normal_items, total_item_counts)
                
                print("DEBUG: Attempting to send !itemlist embed.")
                message_sent_obj = None
                try:
                    message_sent_obj = await message.channel.send(embed=initial_embed)
                    print(f"DEBUG: !itemlist embed sent successfully. Message ID: {message_sent_obj.id}")
                except discord.Forbidden:
                    print(f"ERROR: Bot lacks permissions to send messages in channel {message.channel.id} for !itemlist.")
                    guild_name = (message.guild.name if message.guild else 'DM')
                    await message.author.send(f"申し訳ありません、このチャンネルでアイテムリストを送信する権限がありません。\n"
                                              f"チャンネル名: `{message.channel.name}`, サーバー名: `{guild_name}`")
                    return
                except discord.HTTPException as http_e:
                    print(f"ERROR: HTTPException during !itemlist embed send: {http_e.status} {http_e.text}")
                    await message.channel.send("アイテムリストの送信中にDiscord APIエラーが発生しました。時間を置いて再度お試しください。")
                    return
                except Exception as embed_e:
                    print(f"ERROR: Unexpected error while sending !itemlist embed: {embed_e}")
                    import traceback
                    traceback.print_exc()
                    await message.channel.send("アイテムリストの送信中に予期せぬエラーが発生しました。")
                    return

                if message_sent_obj is None:
                    print("DEBUG: Message_sent_obj is None, stopping !itemlist processing.")
                    return

                pagination_sessions[message_sent_obj.id] = {
                    "user_id": user_id,
                    "current_page": 0,
                    "items_per_page": items_per_page,
                    "current_category": "normal",
                    "normal_items": normal_items,
                    "golden_items": golden_items,
                    "rainbow_items": rainbow_items,
                    "total_item_counts": total_item_counts
                }
                print("DEBUG: Pagination session saved.")

                print("DEBUG: Attempting to add reactions.")
                try:
                    await message_sent_obj.add_reaction('◀️')
                    await message_sent_obj.add_reaction('▶️')
                    await message_sent_obj.add_reaction('🐾')
                    await message_sent_obj.add_reaction('⭐')
                    await message_sent_obj.add_reaction('🌈')
                    print("DEBUG: Reactions added successfully.")
                except discord.Forbidden:
                    print(f"ERROR: Bot lacks permissions to add reactions in channel {message.channel.id}: {e}")
                except discord.HTTPException as http_e:
                    print(f"ERROR: HTTPException during !itemlist reaction add: {http_e.status} {http_e.text}")
                except Exception as react_e:
                    print(f"ERROR: Unexpected error while adding reactions for !itemlist: {react_e}")
                    import traceback
                    traceback.print_exc()

            except Exception as e:
                print(f"ERROR: Failed to process !itemlist command or send embed/reactions (outer try): {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!ranking":
            print("DEBUG: Entering !ranking command block.")
            try:
                async with user_data_lock:
                    sorted_users = sorted(user_data.items(), key=lambda item: item[1].get("rolls", 0), reverse=True)

                embed = discord.Embed(
                    title="ロール数ランキング",
                    description="最も多くロールしたユーザーのトップ10です。",
                    color=discord.Color.gold()
                )

                rank = 1
                for user_id_str, data in sorted_users[:10]:
                    try:
                        user = await bot.fetch_user(int(user_id_str))
                        embed.add_field(name=f"**#{rank} {user.name}**", value=f"ロール数: {data.get('rolls', 0)}", inline=False)
                        rank += 1
                    except discord.NotFound:
                        print(f"WARNING: User not found for ranking display: {user_id_str}")
                        embed.add_field(name=f"**#{rank} 不明なユーザー ({user_id_str})**", value=f"ロール数: {data.get('rolls', 0)}", inline=False)
                        rank += 1
                    except Exception as e:
                        print(f"ERROR: Error during ranking display for user ID: {user_id_str}: {e}")
                        embed.add_field(name=f"**#{rank} エラーユーザー ({user_id_str})**", value=f"ロール数: {data.get('rolls', 0)} (エラー: {e})", inline=False)
                        rank += 1
                if not sorted_users:
                    embed.add_field(name="データなし", value="まだ誰もロールしていません。", inline=False)
                
                print("DEBUG: Attempting to send !ranking embed.")
                await message.channel.send(embed=embed)
                print("DEBUG: !ranking embed sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !ranking command or send embed: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!recipe":
            print("DEBUG: Entering !recipe command block.")
            try:
                embed = discord.Embed(
                    title="Luck Potion 作成レシピ",
                    description="より強力なラックブーストを得るために、Luck Potionを合成しましょう！",
                    color=discord.Color.green()
                )

                for potion_name, recipe_data in LUCK_POTION_RECIPES.items():
                    materials_str = []
                    for material, quantity in recipe_data["materials"].items():
                        materials_str.append(f"{material} x {quantity}個")
                    
                    output_item = list(recipe_data["output"].keys())[0]
                    output_quantity = list(recipe_data["output"].values())[0]
                    luck_multiplier = recipe_data["luck_multiplier"]

                    embed.add_field(
                        name=f"**{potion_name}**",
                        value=f"**効果:** ラック {luck_multiplier:,}倍 (1回のロール)\n"
                              f"**素材:** {', '.join(materials_str)}\n"
                              f"**作成数:** {output_quantity}個",
                        inline=False
                    )
                print("DEBUG: Attempting to send !recipe embed.")
                await message.channel.send(embed=embed)
                print("DEBUG: !recipe embed sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !recipe command or send embed: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!make "):
            print("DEBUG: Entering !make command block.")
            try:
                parts = command_content.split(" ")
                if len(parts) < 3:
                    await message.channel.send("使い方が間違っています。例: `!make rtx4070 1` または `!make rtx4070 all`")
                    return

                target_potion_name_input = parts[1]
                quantity_str = parts[2]

                target_recipe = None
                for potion_name_in_recipe, recipe_data in LUCK_POTION_RECIPES.items():
                    if potion_name_in_recipe.lower() == target_potion_name_input.lower():
                        target_recipe = recipe_data
                        break

                if not target_recipe:
                    await message.channel.send(f"指定されたポーション `{target_potion_name_input}` のレシピが見つかりません。`!recipe`で確認してください。")
                    return

                materials_needed = target_recipe["materials"]
                output_potion_internal_name = list(target_recipe["output"].keys())[0]
                output_potion_quantity_per_craft = list(target_recipe["output"].values())[0]

                async with user_data_lock:
                    user_inventory = user_data[user_id]["inventory"]
                    user_luck_potions = user_data[user_id]["luck_potions"]

                    max_craftable_count = float('inf')
                    for material, needed_quantity in materials_needed.items():
                        if needed_quantity > 0:
                            if material not in user_inventory or user_inventory[material] < needed_quantity:
                                max_craftable_count = 0
                                break
                            max_craftable_count = min(max_craftable_count, user_inventory[material] // needed_quantity)

                    if max_craftable_count == 0:
                        missing_materials = []
                        for material, needed_quantity in materials_needed.items():
                            owned = user_inventory.get(material, 0)
                            if owned < needed_quantity:
                                missing_materials.append(f"{material} ({needed_quantity - owned}個不足)")
                        await message.channel.send(f"素材が足りません！足りない素材: {', '.join(missing_materials)}")
                        return

                    craft_count = 0
                    if quantity_str.lower() == "all":
                        craft_count = max_craftable_count
                    else:
                        try:
                            craft_count = int(quantity_str)
                            if craft_count <= 0:
                                await message.channel.send("作成する個数は1以上である必要があります。")
                                return
                            if craft_count > max_craftable_count:
                                await message.channel.send(f"素材が足りません。最大で{max_craftable_count}個作成できます。")
                                return
                        except ValueError:
                            await message.channel.send("作成する個数は数字か 'all' で指定してください。")
                            return

                    for material, needed_quantity in materials_needed.items():
                        user_inventory[material] -= needed_quantity * craft_count
                        if user_inventory[material] <= 0:
                            del user_inventory[material]

                    total_potions_made = output_potion_quantity_per_craft * craft_count
                    user_luck_potions[output_potion_internal_name] = user_luck_potions.get(output_potion_internal_name, 0) + total_potions_made

                    save_user_data()
                print("DEBUG: Attempting to send !make confirmation message.")
                await message.channel.send(f"{message.author.mention} は **{target_potion_name_input}** を {total_potions_made}個作成しました！")
                print("DEBUG: !make confirmation message sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !make command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!use "):
            print("DEBUG: Entering !use command block.")
            try:
                parts = command_content.split(" ")
                if len(parts) < 3:
                    await message.channel.send("使い方が間違っています。例: `!use rtx4070 1` または `!use rtx4070 all`")
                    return

                target_potion_name_input = parts[1]
                quantity_str = parts[2]

                target_potion_internal_name = None
                for potion_name_in_recipe, recipe_data in LUCK_POTION_RECIPES.items():
                    if potion_name_in_recipe.lower() == target_potion_name_input.lower():
                        if isinstance(recipe_data["output"], dict) and len(recipe_data["output"]) > 0:
                            target_potion_internal_name = list(recipe_data["output"].keys())[0]
                            break

                if not target_potion_internal_name:
                    await message.channel.send(f"指定されたポーション `{target_potion_name_input}` は存在しません。`!recipe`で確認してください。")
                    return

                async with user_data_lock:
                    user_luck_potions = user_data[user_id]["luck_potions"]
                    user_active_uses = user_data[user_id]["active_luck_potion_uses"]

                    owned_count = user_luck_potions.get(target_potion_internal_name, 0)

                    if owned_count == 0:
                        await message.channel.send(f"**{target_potion_name_input}** を所持していません。")
                        return

                    use_count = 0
                    if quantity_str.lower() == "all":
                        use_count = owned_count
                    else:
                        try:
                            use_count = int(quantity_str)
                            if use_count <= 0:
                                await message.channel.send("使用する個数は1以上である必要があります。")
                                return
                            if use_count > owned_count:
                                await message.channel.send(f"所持数が足りません。最大で{owned_count}個使用できます。")
                                return
                        except ValueError:
                            await message.channel.send("使用する個数は数字か 'all' で指定してください。")
                            return

                    user_luck_potions[target_potion_internal_name] -= use_count
                    if user_luck_potions[target_potion_internal_name] <= 0:
                        del user_luck_potions[target_potion_internal_name]

                    user_active_uses[target_potion_internal_name] = user_active_uses.get(target_potion_internal_name, 0) + (use_count * 1)

                    save_user_data()
                print("DEBUG: Attempting to send !use confirmation message.")
                await message.channel.send(f"{message.author.mention} は **{target_potion_name_input}** を {use_count}個使用キューに追加しました。次のロールから効果が適用されます。")
                print("DEBUG: !use confirmation message sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !use command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!craft "):
            print("DEBUG: Entering !craft command block.")
            try:
                parts = command_content.split(" ")
                if len(parts) < 3:
                    await message.channel.send("使い方が間違っています。例: `!craft golden haka 5` または `!craft golden haka all`")
                    return

                target_item_name = " ".join(parts[1:-1])
                quantity_str = parts[-1]

                target_recipe = CRAFTING_RECIPES.get(target_item_name)

                if not target_recipe:
                    await message.channel.send(f"アイテム `{target_item_name}` の合成レシピが見つかりません。")
                    return

                materials_needed = target_recipe["materials"]
                output_item = list(target_recipe["output"].keys())[0]
                output_quantity_per_craft = list(target_recipe["output"].values())[0]

                async with user_data_lock:
                    user_inventory = user_data[user_id]["inventory"]

                    max_craftable_count = float('inf')
                    for material, needed_quantity in materials_needed.items():
                        if needed_quantity > 0:
                            if material not in user_inventory or user_inventory[material] < needed_quantity:
                                max_craftable_count = 0
                                break
                            max_craftable_count = min(max_craftable_count, user_inventory[material] // needed_quantity)

                    if max_craftable_count == 0:
                        missing_materials = []
                        for material, needed_quantity in materials_needed.items():
                            owned = user_inventory.get(material, 0)
                            if owned < needed_quantity:
                                missing_materials.append(f"{material} ({needed_quantity - owned}個不足)")
                        await message.channel.send(f"素材が足りません！足りない素材: {', '.join(missing_materials)}")
                        return

                    craft_count = 0
                    if quantity_str.lower() == "all":
                        craft_count = max_craftable_count
                    else:
                        try:
                            craft_count = int(quantity_str)
                            if craft_count <= 0:
                                await message.channel.send("作成する個数は1以上である必要があります。")
                                return
                            if craft_count > max_craftable_count:
                                await message.channel.send(f"素材が足りません。最大で{max_craftable_count}個作成できます。")
                                return
                        except ValueError:
                            await message.channel.send("作成する個数は数字か 'all' で指定してください。")
                            return

                    for material, needed_quantity in materials_needed.items():
                        user_inventory[material] -= needed_quantity * craft_count
                        if user_inventory[material] <= 0:
                            del user_inventory[material]

                    user_inventory[output_item] = user_inventory.get(output_item, 0) + (output_quantity_per_craft * craft_count)

                    save_user_data()
                print("DEBUG: Attempting to send !craft confirmation message.")
                await message.channel.send(f"{message.author.mention} は **{output_item}** を {output_quantity_per_craft * craft_count}個合成しました！")
                print("DEBUG: !craft confirmation message sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !craft command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!giveluckitem"):
            print("DEBUG: Entering !giveluckitem command block (admin).")
            if message.author.id not in ADMIN_IDS:
                await message.channel.send("このコマンドは管理者のみが使用できます。")
                return
            
            parts = command_content.split(" ")
            if len(parts) < 4:
                await message.channel.send("使い方が間違っています。例: `!giveluckitem rtx4070 @ユーザー名 1`")
                return

            potion_name_input = parts[1]
            target_user_id_or_mention = parts[2]
            quantity_str = parts[3]

            target_potion_internal_name = None
            for p_name_in_recipe, recipe_data in LUCK_POTION_RECIPES.items():
                if p_name_in_recipe.lower() == potion_name_input.lower():
                    target_potion_internal_name = list(recipe_data["output"].keys())[0]
                    break
            
            if not target_potion_internal_name:
                await message.channel.send(f"指定されたLuck Potion `{potion_name_input}` は存在しません。")
                return

            target_user = None
            try:
                if message.mentions and str(message.mentions[0].id) == target_user_id_or_mention.replace("<@", "").replace(">", "").replace("!", ""):
                    target_user = message.mentions[0]
                elif target_user_id_or_mention.isdigit():
                    target_user = await bot.fetch_user(int(target_user_id_or_mention))
                else:
                    await message.channel.send("有効なユーザーメンションまたはIDを指定してください。")
                    return
            except (ValueError, discord.NotFound):
                await message.channel.send("指定されたユーザーが見つかりません。")
                return
            
            if target_user is None:
                await message.channel.send("ユーザーの解決に失敗しました。")
                return

            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    await message.channel.send("個数は正の整数である必要があります。")
                    return
            except ValueError:
                await message.channel.send("個数は数値で指定してください。")
                return
            
            async with user_data_lock:
                target_user_id_str = str(target_user.id)
                # ユーザーデータが存在しない場合は初期化
                if target_user_id_str not in user_data:
                     user_data[target_user_id_str] = {
                        "rolls": 0, "luck": 1.0, "inventory": {}, "luck_potions": {},
                        "active_luck_potion_uses": {},
                        "daily_login": {"last_login_date": None, "consecutive_days": 0, "active_boost": {"multiplier": 1.0, "end_time": None}},
                        "admin_boost": {"multiplier": 1.0, "end_time": None}
                    }
                
                # Luck Potionインベントリの初期化
                if "luck_potions" not in user_data[target_user_id_str]:
                    user_data[target_user_id_str]["luck_potions"] = {}

                user_luck_potions = user_data[target_user_id_str]["luck_potions"]
                user_luck_potions[target_potion_internal_name] = user_luck_potions.get(target_potion_internal_name, 0) + quantity
                save_user_data()
            
            await message.channel.send(f"管理者によって、{target_user.name} に **{potion_name_input}** (内部名: `{target_potion_internal_name}`) が {quantity}個与えられました。")
            try:
                await target_user.send(f"管理者から **{potion_name_input}** (`{target_potion_internal_name}`) が {quantity}個与えられました！")
            except discord.Forbidden:
                print(f"WARNING: Could not DM {target_user.name}. They might have DMs disabled.")

        elif command_content == "!autorng":
            print("DEBUG: Entering !autorng command block (regular user).")
            try:
                target_user = message.author
                target_user_id_str = str(target_user.id)

                if target_user_id_str in auto_rng_sessions and auto_rng_sessions[target_user_id_str]["task"] and not auto_rng_sessions[target_user_id_str]["task"].done():
                    await message.channel.send(f"**{target_user.name}** のオートRNGはすでに実行中です。")
                    return

                session_duration_seconds = 6 * 3600

                auto_rng_sessions[target_user_id_str] = {
                    "task": bot.loop.create_task(auto_roll_task(target_user)),
                    "found_items_log": {},
                    "start_time": datetime.datetime.now(datetime.timezone.utc),
                    "max_duration_seconds": session_duration_seconds
                }
                save_auto_rng_sessions()
                print("DEBUG: Attempting to send !autorng start message.")
                await message.channel.send(f"**{target_user.name}** のオートRNGを開始しました。結果はDMで送信されます。")
                print("DEBUG: !autorng start message sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !autorng command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!giveautorng"):
            print("DEBUG: Entering !giveautorng command block (admin).")
            try:
                if message.author.id not in ADMIN_IDS:
                    await message.channel.send("このコマンドは管理者のみが使用できます。")
                    return

                parts = command_content.split(" ")
                if len(parts) < 2:
                    await message.channel.send("管理者用`!giveautorng`の使い方が間違っています。`!giveautorng @ユーザー名`、`!giveautorng [ユーザーID]`、または`!giveautorng all`")
                    return
                
                target_user_obj_or_all = None
                target_user_id_str = None

                if len(message.mentions) > 0:
                    target_user_obj_or_all = message.mentions[0]
                    target_user_id_str = str(target_user_obj_or_all.id)
                elif parts[1] == "all":
                    target_user_obj_or_all = "all"
                    target_user_id_str = "all"
                else:
                    try:
                        parsed_id = parts[1].replace("<@", "").replace(">", "").replace("!", "")
                        if parsed_id.isdigit():
                            target_user_obj_or_all = await bot.fetch_user(int(parsed_id))
                            target_user_id_str = str(target_user_obj_or_all.id)
                        else:
                            await message.channel.send("無効なユーザー指定です。メンション、ユーザーID、または 'all' を使用してください。")
                            return
                    except (ValueError, discord.NotFound):
                        await message.channel.send("無効なユーザー指定です。メンション、ユーザーID、または 'all' を使用してください。")
                        return

                if target_user_id_str != "all":
                    async with user_data_lock:
                        if target_user_id_str not in user_data:
                            print(f"DEBUG: Initializing user data for {target_user_id_str} via !giveautorng.")
                            user_data[target_user_id_str] = {
                                "rolls": 0,
                                "luck": 1.0,
                                "inventory": {},
                                "luck_potions": {},
                                "active_luck_potion_uses": {},
                                "daily_login": {
                                    "last_login_date": None,
                                    "consecutive_days": 0,
                                    "active_boost": {
                                        "multiplier": 1.0,
                                        "end_time": None
                                    }
                                },
                                "admin_boost": {
                                    "multiplier": 1.0,
                                    "end_time": None
                                }
                            }
                            save_user_data()
                        if "daily_login" not in user_data[target_user_id_str]:
                            user_data[target_user_id_str]["daily_login"] = {
                                "last_login_date": None, "consecutive_days": 0,
                                "active_boost": {"multiplier": 1.0, "end_time": None}
                            }
                        if "luck_potions" not in user_data[target_user_id_str]:
                            user_data[target_user_id_str]["luck_potions"] = {}
                        if "active_luck_potion_uses" not in user_data[target_user_id_str]:
                            user_data[target_user_id_str]["active_luck_potion_uses"] = {}
                        if "admin_boost" not in user_data[target_user_id_str]:
                            user_data[target_user_id_str]["admin_boost"] = {"multiplier": 1.0, "end_time": None}
                        save_user_data()

                if target_user_obj_or_all == "all":
                    await message.channel.send("全ユーザーのオートRNGを開始します。")
                    users_to_start = []
                    async with user_data_lock:
                        for uid_str in list(user_data.keys()):
                            try:
                                user_obj = await bot.fetch_user(int(uid_str))
                                users_to_start.append(user_obj)
                            except discord.NotFound:
                                print(f"WARNING: User {uid_str} not found, skipping for !giveautorng all.")
                    
                    for user_obj in users_to_start:
                        uid_str = str(user_obj.id)
                        async with user_data_lock:
                            if uid_str not in user_data:
                                print(f"DEBUG: Initializing user data for {uid_str} during !giveautorng all.")
                                user_data[uid_str] = {
                                    "rolls": 0, "luck": 1.0, "inventory": {}, "luck_potions": {},
                                    "active_luck_potion_uses": {},
                                    "daily_login": {"last_login_date": None, "consecutive_days": 0, "active_boost": {"multiplier": 1.0, "end_time": None}},
                                    "admin_boost": {"multiplier": 1.0, "end_time": None}
                                }
                                save_user_data()
                            if "daily_login" not in user_data[uid_str]: user_data[uid_str]["daily_login"] = {"last_login_date": None, "consecutive_days": 0, "active_boost": {"multiplier": 1.0, "end_time": None}}; save_user_data()
                            if "luck_potions" not in user_data[uid_str]: user_data[uid_str]["luck_potions"] = {}; save_user_data()
                            if "active_luck_potion_uses" not in user_data[uid_str]: user_data[uid_str]["active_luck_potion_uses"] = {}; save_user_data()
                            if "admin_boost" not in user_data[uid_str]: user_data[uid_str]["admin_boost"] = {"multiplier": 1.0, "end_time": None}; save_user_data()

                        if uid_str in auto_rng_sessions and auto_rng_sessions[uid_str]["task"] and not auto_rng_sessions[uid_str]["task"].done():
                            await message.channel.send(f"**{user_obj.name}** のオートRNGはすでに実行中です。")
                        else:
                            session_duration_seconds = 6 * 3600
                            auto_rng_sessions[uid_str] = {
                                "task": bot.loop.create_task(auto_roll_task(user_obj)),
                                "found_items_log": {},
                                "start_time": datetime.datetime.now(datetime.timezone.utc),
                                "max_duration_seconds": session_duration_seconds
                            }
                            save_auto_rng_sessions()
                            await message.channel.send(f"**{user_obj.name}** のオートRNGを開始しました。結果はDMで送信されます。")
                    return

                if target_user_id_str in auto_rng_sessions and auto_rng_sessions[target_user_id_str]["task"] and not auto_rng_sessions[target_user_id_str]["task"].done():
                    await message.channel.send(f"**{target_user_obj_or_all.name}** のオートRNGはすでに実行中です。")
                    return

                session_duration_seconds = 6 * 3600

                auto_rng_sessions[target_user_id_str] = {
                    "task": bot.loop.create_task(auto_roll_task(target_user_obj_or_all)),
                    "found_items_log": {},
                    "start_time": datetime.datetime.now(datetime.timezone.utc),
                    "max_duration_seconds": session_duration_seconds
                }
                save_auto_rng_sessions()
                print("DEBUG: Attempting to send !giveautorng start message.")
                await message.channel.send(f"**{target_user_obj_or_all.name}** のオートRNGを開始しました。結果はDMで送信されます。")
                print("DEBUG: !giveautorng start message sent.")
            except Exception as e:
                print(f"ERROR: Failed to process !giveautorng command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!autostop":
            print("DEBUG: Entering !autostop command block.")
            try:
                if user_id in auto_rng_sessions and auto_rng_sessions[user_id]["task"] and not auto_rng_sessions[user_id]["task"].done():
                    auto_rng_sessions[user_id]["task"].cancel()
                    print("DEBUG: Attempting to send !autostop confirmation message.")
                    await message.channel.send(f"{message.author.mention} のオートRNGを停止しました。結果はDMで送信されます。")
                    print("DEBUG: !autostop confirmation message sent.")
                else:
                    await message.channel.send(f"{message.author.mention} のオートRNGは現在実行されていません。")
            except Exception as e:
                print(f"ERROR: Failed to process !autostop command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!autorngtime":
            print("DEBUG: Entering !autorngtime command block.")
            try:
                if user_id in auto_rng_sessions and auto_rng_sessions[user_id]["task"] and not auto_rng_sessions[user_id]["task"].done():
                    session_data = auto_rng_sessions[user_id]
                    start_time = session_data["start_time"]
                    max_duration_seconds = session_data["max_duration_seconds"]

                    current_time_utc = datetime.datetime.now(datetime.timezone.utc)
                    elapsed_time = (current_time_utc - start_time).total_seconds()
                    remaining_time_seconds = max_duration_seconds - elapsed_time

                    if remaining_time_seconds <= 0:
                        await message.channel.send(f"{message.author.mention} のオートRNGはすでに終了しています。")
                    else:
                        hours, remainder = divmod(int(remaining_time_seconds), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        print("DEBUG: Attempting to send !autorngtime message.")
                        await message.channel.send(f"{message.author.mention} のオートRNG残り時間: **{hours}時間 {minutes}分 {seconds}秒**")
                        print("DEBUG: !autorngtime message sent.")
                else:
                    await message.channel.send(f"{message.author.mention} のオートRNGは現在実行されていません。")
            except Exception as e:
                print(f"ERROR: Failed to process !autorngtime command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!adminautorng":
            print("DEBUG: Entering !adminautorng command block.")
            try:
                if message.author.id not in ADMIN_IDS:
                    await message.channel.send("このコマンドは管理者のみが使用できます。")
                    return

                active_sessions = []
                for uid, session_data in auto_rng_sessions.items():
                    if session_data["task"] and not session_data["task"].done():
                        try:
                            user_obj = await bot.fetch_user(int(uid))
                            start_time = session_data["start_time"]
                            max_duration_seconds = session_data["max_duration_seconds"]
                            
                            current_time_utc = datetime.datetime.now(datetime.timezone.utc)
                            elapsed_time = (current_time_utc - start_time).total_seconds()
                            remaining_time_seconds = max_duration_seconds - elapsed_time

                            if remaining_time_seconds > 0:
                                hours, remainder = divmod(int(remaining_time_seconds), 3600)
                                minutes, seconds = divmod(remainder, 60)
                                active_sessions.append(f"・{user_obj.name} (ID: {uid}): 残り {hours}h {minutes}m {seconds}s")
                            else:
                                active_sessions.append(f"・{user_obj.name} (ID: {uid}): 期限切れ (データ更新待ち)")
                        except discord.NotFound:
                            print(f"WARNING: User not found for adminautorng display: {uid}")
                            active_sessions.append(f"・不明なユーザー (ID: {uid}): (ユーザーが見つかりません)")
                        except Exception as e:
                            print(f"ERROR: Error during adminautorng display for user ID: {uid}: {e}")
                            active_sessions.append(f"・{uid}: データの読み込みエラー ({e})")

                if active_sessions:
                    embed = discord.Embed(
                        title="現在実行中のオートRNGセッション",
                        description="\n".join(active_sessions),
                        color=discord.Color.red()
                    )
                    print("DEBUG: Attempting to send !adminautorng embed.")
                    await message.channel.send(embed=embed)
                    print("DEBUG: !adminautorng embed sent.")
                else:
                    await message.channel.send("現在、実行中のオートRNGセッションはありません。")
            except Exception as e:
                print(f"ERROR: Failed to process !adminautorng command or send embed: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!boostluck"):
            print("DEBUG: Entering !boostluck command block.")
            try:
                if message.author.id not in ADMIN_IDS:
                    await message.channel.send("このコマンドは管理者のみが使用できます。")
                    return

                parts = command_content.split(" ")
                if len(parts) != 3:
                    await message.channel.send("使い方が間違っています。例: `!boostluck 1.5 60` (1.5倍、60秒)")
                    return

                try:
                    multiplier = float(parts[1])
                    duration_seconds = int(parts[2])
                    if multiplier <= 0 or duration_seconds <= 0:
                        await message.channel.send("倍率と秒数は正の数である必要があります。")
                        return
                except ValueError:
                    await message.channel.send("倍率と秒数は数値で指定してください。")
                    return

                end_time_timestamp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=duration_seconds)).timestamp()

                async with user_data_lock:
                    for uid in user_data:
                        user_data[uid]["luck"] = multiplier 
                        user_data[uid]["admin_boost"] = {
                            "multiplier": multiplier,
                            "end_time": end_time_timestamp
                        }
                    save_user_data()

                print("DEBUG: Attempting to send !boostluck start message.")
                await message.channel.send(f"全員のラックを一時的に **{multiplier:.1f}倍** にしました！ ({duration_seconds}秒間有効)")
                print("DEBUG: !boostluck start message sent.")

                await asyncio.sleep(duration_seconds)

                async with user_data_lock:
                    for uid in user_data:
                        user_data[uid]["luck"] = 1.0
                        user_data[uid]["admin_boost"] = {
                            "multiplier": 1.0,
                            "end_time": None
                        }
                    save_user_data()
                await message.channel.send("全員のラックブーストが終了し、元のラックに戻りました。")
            except Exception as e:
                print(f"ERROR: Failed to process !boostluck command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!resetall":
            print("DEBUG: Entering !resetall command block.")
            try:
                if message.author.id not in ADMIN_IDS:
                    await message.channel.send("このコマンドは管理者のみが使用できます。")
                    return

                await message.channel.send("**警告: 全ユーザーのデータがリセットされます。本当に実行しますか？ `yes` と入力して10秒以内に送信してください。**")

                def check(m):
                    return m.author == message.author and m.channel == message.channel and m.content.lower() == 'yes'

                try:
                    confirm_message = await bot.wait_for('message', check=check, timeout=10.0)
                    if confirm_message:
                        async with user_data_lock:
                            user_data = {}
                            save_user_data()

                            for session_id, session_data in auto_rng_sessions.items():
                                if session_data["task"] and not session_data["task"].done():
                                    session_data["task"].cancel()
                            auto_rng_sessions = {}
                            save_auto_rng_sessions()

                            async with daily_summary_state_lock:
                                reset_state = {
                                    "last_processed_date": None,
                                    "rolls_since_last_processed": 0,
                                    "most_rare_item_today_info": {
                                        "item_name": None,
                                        "original_denominator": 0,
                                        "finder_id": None,
                                        "timestamp": None
                                    }
                                }
                                save_daily_summary_state_main(reset_state)

                        await message.channel.send("全ユーザーのデータとオートRNGセッションがリセットされました。")
                except asyncio.TimeoutError:
                    await message.channel.send("確認がタイムアウトしました。データのリセットはキャンセルされました。")
                except Exception as e:
                    print(f"ERROR: Error during !resetall confirmation or processing: {e}")
                    import traceback
                    traceback.print_exc()
            except Exception as e:
                print(f"ERROR: Failed to process !resetall command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content.startswith("!delete"):
            print("DEBUG: Entering !delete command block (admin).")
            try:
                if message.author.id not in ADMIN_IDS:
                    await message.channel.send("このコマンドは管理者のみが使用できます。")
                    return
                
                parts = command_content.split(" ")
                if len(parts) < 2:
                    await message.channel.send("使い方が間違っています。例: `!delete @ユーザー名`, `!delete [ユーザーID]`, または `!delete all`")
                    return

                target = parts[1]
                target_user_ids_to_delete = []
                target_names_to_report = []

                if target == "all":
                    target_user_ids_to_delete = list(user_data.keys())
                    target_names_to_report = ["全ユーザー"]
                else:
                    user_obj = None
                    try:
                        parsed_id = target.replace("<@", "").replace(">", "").replace("!", "")
                        if message.mentions and str(message.mentions[0].id) == parsed_id: 
                            user_obj = message.mentions[0]
                        elif parsed_id.isdigit():
                            user_obj = await bot.fetch_user(int(parsed_id))
                        else:
                            await message.channel.send("無効なユーザー指定です。メンションまたは有効なユーザーIDを使用してください。")
                            return
                        target_user_ids_to_delete.append(str(user_obj.id))
                        target_names_to_report.append(user_obj.name)
                    except (ValueError, discord.NotFound):
                        await message.channel.send("指定されたユーザーが見つかりません。メンションまたは有効なユーザーIDを使用してください。")
                        return
                
                if not target_user_ids_to_delete:
                    await message.channel.send("削除対象のユーザーが指定されていません。")
                    return

                confirmation_message_text = f"**警告: {', '.join(target_names_to_report)} の全てのデータが削除されます。** オートRNGセッションも停止されます。本当に実行しますか？ `yes` と入力して10秒以内に送信してください。"
                await message.channel.send(confirmation_message_text)

                def check(m):
                    return m.author == message.author and m.channel == message.channel and m.content.lower() == 'yes'

                try:
                    confirm_message = await bot.wait_for('message', check=check, timeout=10.0)
                    if confirm_message:
                        async with user_data_lock:
                            for uid_to_delete in target_user_ids_to_delete:
                                if uid_to_delete in user_data:
                                    del user_data[uid_to_delete]
                                    print(f"DEBUG: Deleted user data for {uid_to_delete}.")
                                
                                if uid_to_delete in auto_rng_sessions:
                                    if auto_rng_sessions[uid_to_delete]["task"] and not auto_rng_sessions[uid_to_delete]["task"].done():
                                        auto_rng_sessions[uid_to_delete]["task"].cancel()
                                        print(f"DEBUG: Cancelled auto-RNG task for {uid_to_delete}.")
                                    del auto_rng_sessions[uid_to_delete]
                                    print(f"DEBUG: Deleted auto-RNG session for {uid_to_delete}.")
                                
                                if uid_to_delete in last_auto_rng_save_rolls:
                                    del last_auto_rng_save_rolls[uid_to_delete]
                                if uid_to_delete in last_auto_rng_save_time:
                                    del last_auto_rng_save_time[uid_to_delete]
                            
                            save_user_data()
                            save_auto_rng_sessions()
                            await message.channel.send(f"{', '.join(target_names_to_report)} のデータとオートRNGセッションが削除されました。")
                    else:
                        await message.channel.send("確認が一致しませんでした。データ削除はキャンセルされました。")
                except asyncio.TimeoutError:
                    await message.channel.send("確認がタイムアウトしました。データ削除はキャンセルされました。")
                except Exception as e:
                    print(f"ERROR: Error during !delete command processing: {e}")
                    import traceback
                    traceback.print_exc()
                    await message.channel.send(f"データ削除中にエラーが発生しました: {e}")

            except Exception as e:
                print(f"ERROR: Failed to process !delete command or send message: {e}")
                import traceback
                traceback.print_exc()

        elif command_content == "!test":
            print("DEBUG: Entering !test command block.")
            try:
                await message.channel.send("ボットは正常に動作しています！")
                print("DEBUG: !test response sent.")
            except Exception as e:
                print(f"ERROR: Failed to send !test response: {e}")
                import traceback
                traceback.print_exc()
        
        else:
            print(f"DEBUG: Command '{command_content}' not recognized or handled.")

    except Exception as e:
        print(f"CRITICAL ERROR in on_message function! Please review the traceback below:")
        import traceback
        traceback.print_exc()

AUTO_RNG_SAVE_INTERVAL_ROLLS = 100
AUTO_RNG_SAVE_INTERVAL_SECONDS = 60
last_auto_rng_save_time = {}
last_auto_rng_save_rolls = {}

async def auto_roll_task(user: discord.User, is_resumed: bool = False):
    """
    指定されたユーザーの自動ロールを実行する非同期タスク。
    ラックポーションの効果はオートRNGには適用されません。
    """
    user_id = str(user.id)
    session_data = auto_rng_sessions[user_id]
    found_items_log = session_data["found_items_log"]
    start_time = session_data["start_time"]
    max_duration_seconds = session_data["max_duration_seconds"]

    async with user_data_lock:
        initial_rolls = user_data[user_id].get("rolls", 0)
        last_auto_rng_save_rolls[user_id] = initial_rolls
        last_auto_rng_save_time[user_id] = time.time()

    try:
        if is_resumed:
            current_time_utc = datetime.datetime.now(datetime.timezone.utc)
            elapsed_time = (current_time_utc - start_time).total_seconds()
            remaining_time = max_duration_seconds - elapsed_time
            if remaining_time <= 0:
                async with user_data_lock:
                    rolls_performed = user_data[user_id].get("rolls", 0) - initial_rolls
                try:
                    await send_auto_rng_results(user, found_items_log, rolls_performed, "再開前に時間切れ")
                except Exception as e:
                    print(f"WARNING: Could not send auto-RNG results (time out on resume) to {user.name}: {e}")
                
                if user_id in auto_rng_sessions:
                    del auto_rng_sessions[user_id]
                    save_auto_rng_sessions()
                if user_id in last_auto_rng_save_rolls:
                    del last_auto_rng_save_rolls[user_id]
                if user_id in last_auto_rng_save_time:
                    del last_auto_rng_save_time[user_id]
                return

            try:
                await user.send(f"オートRNGセッションを再開します。残り約 {remaining_time / 3600:.1f}時間です。")
            except Exception as e:
                print(f"WARNING: Could not send auto-RNG resume message to {user.name}: {e}")
            await asyncio.sleep(1)

        while True:
            current_time_in_task = datetime.datetime.now(datetime.timezone.utc)

            elapsed_time = (current_time_in_task - start_time).total_seconds()
            if elapsed_time >= max_duration_seconds:
                async with user_data_lock:
                    rolls_performed = user_data[user_id].get("rolls", 0) - initial_rolls
                try:
                    await send_auto_rng_results(user, found_items_log, rolls_performed, "時間切れ")
                except Exception as e:
                    print(f"WARNING: Could not send auto-RNG results (time out) to {user.name}: {e}")
                break

            async with user_data_lock:
                current_base_luck = user_data[user_id]["luck"]

                user_boost = user_data[user_id]["daily_login"]["active_boost"]
                if user_boost["end_time"] and current_time_in_task < datetime.datetime.fromtimestamp(user_boost["end_time"], tz=datetime.timezone.utc):
                    current_base_luck *= user_boost["multiplier"]
                
                admin_boost_info = user_data[user_id].get("admin_boost", {"multiplier": 1.0, "end_time": None})
                if admin_boost_info["end_time"] and current_time_in_task < datetime.datetime.fromtimestamp(admin_boost_info["end_time"], tz=datetime.timezone.utc):
                    current_base_luck *= admin_boost_info["multiplier"]

                # Luck Potionの適用ロジックをオートRNGから削除
                current_luck_for_roll = current_base_luck # Luck Potionは適用しない

                user_data[user_id]["rolls"] = user_data[user_id].get("rolls", 0) + 1
                chosen_item, luck_applied_denominator, original_denominator = perform_roll(current_luck_for_roll, user_id)

                inventory = user_data[user_id]["inventory"]
                inventory[chosen_item] = inventory.get(chosen_item, 0) + 1

                found_items_log[chosen_item] = found_items_log.get(chosen_item, 0) + 1

                async with daily_summary_state_lock:
                    current_daily_state = load_daily_summary_state_main()
                    current_most_rare_info = current_daily_state["most_rare_item_today_info"]

                    if original_denominator > current_most_rare_info["original_denominator"]:
                        current_daily_state["most_rare_item_today_info"] = {
                            "item_name": chosen_item,
                            "original_denominator": original_denominator,
                            "finder_id": user_id,
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp()
                        }
                        save_daily_summary_state_main(current_daily_state)
                        print(f"INFO: Daily most rare item updated for auto-RNG: {chosen_item} by {user_id}")

                current_rolls_count = user_data[user_id]["rolls"]
                current_time_for_save = time.time()

                should_save = False
                if current_rolls_count - last_auto_rng_save_rolls.get(user_id, 0) >= AUTO_RNG_SAVE_INTERVAL_ROLLS:
                    should_save = True
                    print(f"DEBUG: Auto-RNG save triggered by rolls for {user.name}")
                if current_time_for_save - last_auto_rng_save_time.get(user_id, current_time_for_save) >= AUTO_RNG_SAVE_INTERVAL_SECONDS:
                    should_save = True
                    print(f"DEBUG: Auto-RNG save triggered by time for {user.name}")

                if should_save:
                    save_user_data()
                    save_auto_rng_sessions()
                    last_auto_rng_save_rolls[user_id] = current_rolls_count
                    last_auto_rng_save_time[user_id] = current_time_for_save
                    print(f"DEBUG: Auto-RNG data saved for {user.name}.")

            if original_denominator >= 100000:
                notification_channel_id = bot_settings.get("notification_channel_id")
                if notification_channel_id:
                    notification_channel = bot.get_channel(notification_channel_id)
                    if notification_channel:
                        total_item_counts = {item: 0 for item in rare_item_chances_denominator.keys()}
                        async with user_data_lock:
                            for uid_all in user_data:
                                for item, count in user_data[uid_all]["inventory"].items():
                                    if item in total_item_counts:
                                        total_item_counts[item] += count

                        total_owned_count = total_item_counts.get(chosen_item, 0)

                        notification_embed = discord.Embed(
                            title="レアアイテムドロップ通知！ (オートRNG)",
                            description=f"{user.mention} がオートRNGでレアアイテムを獲得しました！",
                            color=discord.Color.gold()
                        )
                        notification_embed.add_field(name="獲得者", value=user.mention, inline=False)
                        notification_embed.add_field(name="アイテム", value=chosen_item, inline=False)
                        notification_embed.add_field(name="確率", value=f"1 in {original_denominator:,}", inline=False)
                        notification_embed.add_field(name="獲得日時", value=datetime.datetime.now(datetime.timezone.utc).strftime("%Y年%m月%d日 %H:%M:%S UTC"), inline=False)
                        notification_embed.add_field(name="サーバー総所持数", value=f"{total_owned_count}個", inline=False)
                        notification_embed.set_footer(text="おめでとうございます！")
                        try:
                            await notification_channel.send(embed=notification_embed)
                        except Exception as e:
                            print(f"WARNING: Could not send rare item notification to channel {notification_channel.id}: {e}")
                    else:
                        print(f"WARNING: Configured notification channel ID {notification_channel_id} not found.")

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        async with user_data_lock:
            rolls_performed = user_data[user_id].get("rolls", 0) - initial_rolls
        try:
            await send_auto_rng_results(user, found_items_log, rolls_performed, "手動停止")
        except Exception as e:
            print(f"WARNING: Could not send auto-RNG results (manual stop) to {user.name}: {e}")
    except Exception as e:
        print(f"ERROR: Auto-RNG error (user ID: {user_id}): {e}")
        import traceback
        traceback.print_exc()
        try:
            await user.send(f"オートRNG中にエラーが発生しました: {e}")
        except Exception as dm_e:
            print(f"WARNING: Could not send error message to user {user.name}: {dm_e}")
    finally:
        if user_id in auto_rng_sessions:
            del auto_rng_sessions[user_id]
            save_auto_rng_sessions()
        if user_id in last_auto_rng_save_rolls:
            del last_auto_rng_save_rolls[user_id]
        if user_id in last_auto_rng_save_time:
            del last_auto_rng_save_time[user_id]
        print(f"DEBUG: Auto-RNG session for {user.name} finished/cleaned up.")

bot.run(os.environ['DISCORD_BOT_TOKEN'])