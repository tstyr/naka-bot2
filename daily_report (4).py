import datetime
import json
import os
import time
import discord # Discord API とのやり取りのため
import asyncio # Discord API との非同期通信のため

# --- 設定 ---
USER_DATA_FILE = 'user_data.json'
BOT_SETTINGS_FILE = 'bot_settings.json' # 通知チャンネルID取得用
DAILY_SUMMARY_STATE_FILE = 'daily_summary_state.json' # 日次集計の状態を保存するファイル

# Discord Bot Token (このスクリプト専用の、メッセージ送信権限のみを持つトークンが良いでしょう)
# 環境変数から取得するのが推奨
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN_DAILY_REPORT') 
# もしメインボットと同じトークンを使うなら、メインボットのトークン環境変数を使用
# DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']

# 各アイテムの基本確率 (perform_rollからコピー)
# 日次レポートでレアリティ比較を行うために必要
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
    "激ヤバみず": 10000000000, # 100億分の1
    "ねこぶる": 100000,       # 10万分の1
    "pro bot": 5000           # 5000分の1
}

def generate_item_data_for_chances(base_chances):
    all_item_chances = {}
    for item_name, base_chance in base_chances.items():
        all_item_chances[item_name] = base_chance
        all_item_chances[f"golden {item_name}"] = base_chance * 10
        all_item_chances[f"rainbow {item_name}"] = base_chance * 100
    return all_item_chances

RARE_ITEM_CHANCES_DENOMINATOR = generate_item_data_for_chances(base_item_chances_denominator)


# --- グローバル変数 (このスクリプト内でのみ使用) ---
# 日次サマリーの状態をファイルからロード/保存
daily_summary_state = {
    "last_processed_date": None, # 最後に集計された日付 (YYYY-MM-DD)
    "rolls_since_last_processed": 0, # 前回集計されてから、現在のデータファイルが持つロール数
    "most_rare_item_today_info": { # 前回の集計から最もレアなアイテム情報
        "item_name": None,
        "original_denominator": 0, 
        "finder_id": None,
        "timestamp": None
    }
}

# --- 状態管理ファイルの保存・ロード ---
def load_daily_summary_state():
    global daily_summary_state
    if os.path.exists(DAILY_SUMMARY_STATE_FILE):
        with open(DAILY_SUMMARY_STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                loaded_state = json.load(f)
                # ロードしたデータが古い形式の場合に備えて初期化
                daily_summary_state["last_processed_date"] = loaded_state.get("last_processed_date")
                daily_summary_state["rolls_since_last_processed"] = loaded_state.get("rolls_since_last_processed", 0)
                daily_summary_state["most_rare_item_today_info"] = loaded_state.get("most_rare_item_today_info", {
                    "item_name": None, "original_denominator": 0, "finder_id": None, "timestamp": None
                })
                print("INFO: Daily summary state loaded.")
            except json.JSONDecodeError as e:
                print(f"ERROR: {DAILY_SUMMARY_STATE_FILE} の読み込み中にエラーが発生しました: {e}")
                print(f"既存の {DAILY_SUMMARY_STATE_FILE} をバックアップし、新しく空のデータを作成します。")
                os.rename(DAILY_SUMMARY_STATE_FILE, DAILY_SUMMARY_STATE_FILE + ".bak." + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                daily_summary_state = {
                    "last_processed_date": None, "rolls_since_last_processed": 0,
                    "most_rare_item_today_info": {"item_name": None, "original_denominator": 0, "finder_id": None, "timestamp": None}
                }
    else:
        print(f"INFO: {DAILY_SUMMARY_STATE_FILE} が見つかりませんでした。新規作成します。")
    save_daily_summary_state() # 初回ロード時に整合性を確保するため保存

def save_daily_summary_state():
    with open(DAILY_SUMMARY_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(daily_summary_state, f, ensure_ascii=False, indent=4)

# --- Discord Client (レポート送信専用) ---
# レポート送信専用のクライアントを作成
report_bot_client = discord.Client(intents=discord.Intents.default()) # メッセージ読み取りは不要

@report_bot_client.event
async def on_ready():
    print(f"INFO: Report bot logged in as {report_bot_client.user}")
    # bot.logout() # ログインしたらすぐにログアウトしてもよいが、通知のために接続を維持

async def send_daily_summary_report(channel_id, total_rolls_overall, rolls_today, most_rare_item):
    channel = report_bot_client.get_channel(channel_id)
    if not channel:
        try:
            channel = await report_bot_client.fetch_channel(channel_id)
        except discord.NotFound:
            print(f"ERROR: Notification channel {channel_id} not found for daily report.")
            return
        except discord.Forbidden:
            print(f"ERROR: Bot is forbidden from accessing channel {channel_id} for daily report.")
            return

    if not channel:
        return

    embed = discord.Embed(
        title=f"📅 {daily_summary_state['last_processed_date']} のデイリーリザルト！",
        color=discord.Color.blue()
    )
    embed.add_field(name="今日の総ロール数", value=f"{rolls_today:,} 回", inline=False)
    
    if most_rare_item["item_name"]:
        finder_name = "不明なユーザー"
        if most_rare_item["finder_id"]:
            try:
                finder_user = await report_bot_client.fetch_user(int(most_rare_item["finder_id"]))
                finder_name = finder_user.name
            except discord.NotFound:
                print(f"WARNING: Finder user (ID: {most_rare_item['finder_id']}) not found for daily report.")
                finder_name = f"不明なユーザー (ID: {most_rare_item['finder_id']})"
            except Exception as e:
                print(f"WARNING: Could not fetch finder user for daily report: {e}")
                finder_name = f"不明なユーザー (ID: {most_rare_item['finder_id']})"

        item_timestamp_utc = datetime.datetime.fromtimestamp(most_rare_item["timestamp"], tz=datetime.timezone.utc)
        item_time_jst = item_timestamp_utc.astimezone(datetime.timezone(datetime.timedelta(hours=9))) # JSTに変換

        embed.add_field(
            name="本日最もレアなドロップ！",
            value=(f"**{most_rare_item['item_name']}** (1 in {most_rare_item['original_denominator']:,})\n"
                   f"獲得者: {finder_name}\n"
                   f"時刻: {item_time_jst.strftime('%H:%M:%S JST')}"),
            inline=False
        )
    else:
        embed.add_field(name="本日最もレアなドロップ！", value="なし（アイテムがドロップしませんでした）", inline=False)
    
    embed.add_field(name="これまでの総ロール数", value=f"{total_rolls_overall:,} 回", inline=False)
    embed.set_footer(text="明日も幸運を！")

    try:
        await channel.send(embed=embed)
        print(f"INFO: Daily summary sent to channel {channel.name}")
    except Exception as e:
        print(f"ERROR: Failed to send daily summary to channel {channel.id}: {e}")

# --- メイン実行ロジック ---
async def main_daily_report_logic():
    print("INFO: Starting daily report logic...")
    
    load_daily_summary_state() # 状態をロード

    # bot_settings から通知チャンネルIDを取得
    bot_settings = {}
    if os.path.exists(BOT_SETTINGS_FILE):
        with open(BOT_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            try:
                bot_settings = json.load(f)
            except json.JSONDecodeError as e:
                print(f"ERROR: {BOT_SETTINGS_FILE} の読み込み中にエラーが発生しました: {e}")
                return

    notification_channel_id = bot_settings.get("notification_channel_id")
    if not notification_channel_id:
        print("WARNING: Notification channel ID is not set in bot_settings.json. Cannot send daily report.")
        return

    # user_data.json の現在のロール総数を取得
    current_user_data = {}
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                current_user_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: user_data.json の読み込み中にエラーが発生しました: {e}")
            return
    
    total_rolls_current = 0
    for user_id in current_user_data:
        total_rolls_current += current_user_data[user_id].get("rolls", 0)

    # 日次バックアップの実行
    backup_filename = f"user_data_backup_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f_read:
            main_data_content = f_read.read()
        with open(backup_filename, 'w', encoding='utf-8') as f_write:
            f_write.write(main_data_content)
        print(f"INFO: user_data.json backed up to {backup_filename}")
    except Exception as e:
        print(f"ERROR: Failed to backup user_data.json: {e}")
        # バックアップ失敗してもレポートは続行


    # 今日のロール回数を計算し、最もレアなアイテムを特定
    rolls_today = 0
    
    # daily_summary_stateに保存されている「最もレアなアイテム」を今回のレポートに使用
    # この情報がどこで更新されるかが重要。メインボット側でロール時に更新されることを想定。
    most_rare_item_for_report = daily_summary_state["most_rare_item_today_info"]


    # 最後に処理された日付が今日と異なる場合のみ、レポートを作成し状態を更新
    # これにより、スクリプトが複数回実行されてもレポートが重複しないようにする
    current_date_str = datetime.datetime.now(datetime.timezone.utc).date().strftime("%Y-%m-%d")
    if daily_summary_state["last_processed_date"] != current_date_str:
        print(f"INFO: Generating daily report for {daily_summary_state['last_processed_date'] or 'previous period'}...")

        # 前回の集計からのロール差分を計算
        rolls_today = total_rolls_current - daily_summary_state["rolls_since_last_processed"]

        # レポート送信
        print(f"INFO: Attempting to send daily report to channel ID: {notification_channel_id}")
        await send_daily_summary_report(notification_channel_id, total_rolls_current, rolls_today, most_rare_item_for_report)
        print("INFO: Daily report sent attempt finished.")

        # 状態を更新して保存
        daily_summary_state["last_processed_date"] = current_date_str
        daily_summary_state["rolls_since_last_processed"] = total_rolls_current
        # 最もレアなアイテム情報はリセット（次の日のために）
        daily_summary_state["most_rare_item_today_info"] = {
            "item_name": None, "original_denominator": 0, "finder_id": None, "timestamp": None
        }
        save_daily_summary_state()
        print("INFO: Daily summary state updated and saved.")
    else:
        print(f"INFO: Daily report for {current_date_str} already processed. Skipping report generation.")
    
    print("INFO: Daily report logic finished.")


# スクリプトを非同期で実行
if __name__ == "__main__":
    # このクライアントはレポート送信にのみ使用
    async def run_report_client_and_logic():
        try:
            # Discordにログインし、on_readyが呼ばれるのを待つ
            await report_bot_client.start(DISCORD_BOT_TOKEN)
        except Exception as e:
            print(f"ERROR: Report bot failed to login or run: {e}")
            
    # メインのレポートロジックを、ログイン後に実行される非同期タスクとしてスケジュール
    # on_ready 内で直接 await すると、on_ready が完了するまで bot が完全に起動しないため、
    # 別タスクとして起動
    async def start_report_logic_after_ready():
        await report_bot_client.wait_until_ready()
        await main_daily_report_logic()
        await report_bot_client.close() # 処理が完了したらクライアントを閉じる

    # イベントループを取得し、タスクを実行
    loop = asyncio.get_event_loop()
    # run_until_complete() はイベントループがすでに実行中の場合はエラーになるため、
    # 別のスレッドで実行するか、try-except でラップして対処が必要
    # Replit の Run ボタンで実行する場合、loop はまだ実行されていないはず
    try:
        loop.run_until_complete(start_report_logic_after_ready())
    except RuntimeError as e:
        if "cannot run a new event loop while the old one is still running" in str(e):
            print("WARNING: Event loop already running, likely in an IDE or notebook. Running as a task.")
            asyncio.create_task(start_report_logic_after_ready())
        else:
            raise e