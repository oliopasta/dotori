import discord
from discord import app_commands
import json
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
import pytz
import urllib.parse
import re
import io
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ================ [설정 및 상수] ================
class Config:
    # 환경 변수에서 키를 불러옵니다.
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')
    LOL_API_KEY = os.getenv('LOL_API_KEY')
    
    TELEGRAM_CHATS_FILE = 'telegram_chats.json'
    VAL_MATCH_URL = "https://vlrggapi.vercel.app/match?q=upcoming"
    VAL_LIVE_URL = "https://vlrggapi.vercel.app/match?q=live_score"
    VAL_SEASON_URL = "https://valorant-api.com/v1/seasons/competitive"
    VAL_PATCH_URL = "https://api.henrikdev.xyz/valorant/v1/website/ko-kr"
    
    LOL_LEAGUES = {
        "First Stand": "113464388705111224", "LCK": "98767991310872058",
        "MSI": "98767991325878492", "Worlds": "98767975604431411"   
    }

    TIER1_TEAMS = {
        '100 Thieves', 'Cloud9', 'Evil Geniuses', 'FURIA', 'KRÜ Esports',
        'Leviatán', 'LOUD', 'MIBR', 'NRG', 'Sentinels', 'G2 Esports', 'ENVY',
        'All Gamers', 'Bilibili Gaming', 'EDward Gaming', 'FunPlus Phoenix',
        'JDG Esports', 'Nova Esports', 'Titan Esports Club', 'Trace Esports',
        'TYLOO', 'Wolves Esports', 'Dragon Ranger Gaming', 'Xi Lai Gaming',
        'BBL Esports', 'FNATIC', 'FUT Esports', 'Karmine Corp', 'Team Vitality',
        'Natus Verni', 'Team Heretics', 'Team Liquid', 'PCIFIC Espor',
        'Gentle Mates', 'GIANTX', 'ULP Esports', 'DetonatioN FocusMe', 'DRX',
        'Gen.G', 'Global Esports', 'Paper Rex', 'Rex Regum Qeon', 'T1', 'TALON',
        'Team Secret', 'ZETA DIVISION', 'Nongshim RedForce', 'VARREL'
    }

# ================ [유틸리티] ================
class Utils:
    @staticmethod
    def get_kst_now():
        return datetime.now(pytz.timezone('Asia/Seoul'))

    @staticmethod
    def format_timestamp(dt=None):
        if dt is None: dt = Utils.get_kst_now()
        return dt.strftime('%y.%m.%d %H:%M:%S')

    @staticmethod
    async def fetch_json(url, headers=None, params=None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            print(f"API Error ({url}): {e}")
            return None

    @staticmethod
    def html_to_discord(html_text):
        text = html_text
        text = text.replace('<b>', '**').replace('</b>', '**')
        text = text.replace('<i>', '*').replace('</i>', '*')
        text = text.replace('<u>', '__').replace('</u>', '__')
        text = text.replace('<code>', '`').replace('</code>', '`')
        text = text.replace('<pre>', '```\n').replace('</pre>', '\n```')
        text = re.sub(r"<a href='([^']+)'>([^<]+)</a>", r"[\2](\1)", text)
        return text

# ================ [서비스 로직] ================
class ValorantService:
    @staticmethod
    def get_current_league_path(region):
        now = Utils.get_kst_now()
        month = now.month
        
        region_map = {
            'Pacific': 'Pacific_League',
            'Americas': 'Americas_League',
            'EMEA': 'EMEA_League',
            'China': 'China_League'
        }

        if region == 'Masters/Champions':
            if 1 <= month <= 4: return "VCT/2026/Stage_1/Masters"
            if 5 <= month <= 7: return "VCT/2026/Stage_2/Masters"
            return "VCT/2026/Champions"

        path_prefix = f"VCT/2026/{region_map.get(region, 'Pacific_League')}"
        if 1 <= month <= 2: return f"{path_prefix}/Kickoff"
        elif 3 <= month <= 5: return f"{path_prefix}/Stage_1"
        elif 6 <= month <= 8: return f"{path_prefix}/Stage_2"
        return f"{path_prefix}/Stage_2"

    @staticmethod
    async def capture_bracket(league_path):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 5000, 'height': 2000}, color_scheme='dark')
            page = await context.new_page()
            url = f"https://liquipedia.net/valorant/{league_path}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                bracket_selector = ".brkts-bracket"
                bracket = page.locator(bracket_selector).first
                await bracket.wait_for(state="visible", timeout=10000)
                await page.evaluate("""(sel) => {
                    const el = document.querySelector(sel);
                    if (el) { el.style.width = 'max-content'; el.style.maxWidth = 'none'; el.style.overflow = 'visible'; }
                }""", bracket_selector)
                await asyncio.sleep(2)
                img_bytes = await bracket.screenshot()
                await browser.close()
                return io.BytesIO(img_bytes)
            except Exception as e:
                print(f"Capture Error: {e}")
                await browser.close()
                return None

    @staticmethod
    async def get_matches_message():
        live_data = await Utils.fetch_json(Config.VAL_LIVE_URL) or {}
        upcoming_data = await Utils.fetch_json(Config.VAL_MATCH_URL) or {}
        live_segments = live_data.get('data', {}).get('segments', [])
        upcoming_segments = upcoming_data.get('data', {}).get('segments', [])
        all_matches = []
        now_kst = Utils.get_kst_now()

        for m in live_segments:
            t1, t2 = m.get('team1', 'TBD'), m.get('team2', 'TBD')
            if t1 not in Config.TIER1_TEAMS and t2 not in Config.TIER1_TEAMS: continue
            event_name = m.get('match_event', '')
            region = "vct"
            if "Americas" in event_name: region += " americas"
            elif "EMEA" in event_name: region += " emea"
            elif "Pacific" in event_name: region += " pacific"
            elif "CN" in event_name: region += " cn"
            search_query = f"{region} {t1} {t2}".replace(" ", "+").lower()
            yt_link = f"https://www.youtube.com/results?search_query={search_query}"
            all_matches.append({
                'event': event_name, 't1': t1, 't2': t2,
                'status': f"<a href='{yt_link}'>{t1} vs {t2}</a> <b>(Live)</b>",
                'is_live': True, 'sort_key': 0
            })

        for m in upcoming_segments:
            t1, t2 = m.get('team1', 'TBD'), m.get('team2', 'TBD')
            if t1 not in Config.TIER1_TEAMS and t2 not in Config.TIER1_TEAMS: continue
            if m.get('unix_timestamp'):
                try:
                    utc = datetime.strptime(m['unix_timestamp'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    kst_match = utc.astimezone(pytz.timezone('Asia/Seoul'))
                    if kst_match < now_kst: continue
                    time_str = kst_match.strftime("%m.%d %H:%M")
                    all_matches.append({
                        'event': m.get('match_event', ''), 't1': t1, 't2': t2,
                        'status': f"{t1} vs {t2} <i>({time_str})</i>",
                        'is_live': False, 'sort_key': kst_match.timestamp()
                    })
                except: continue

        if not all_matches: return "🎮 <b>현재 진행 중이거나 예정된 1군 경기가 없습니다.</b>"
        all_matches.sort(key=lambda x: x['sort_key'])
        msg, tournaments = "", {}
        for m in all_matches: tournaments.setdefault(m['event'], []).append(m)
        for event, m_list in tournaments.items():
            msg += f"<b>[{event}]</b>\n"
            for m in m_list: msg += f"{m['status']}\n"
            msg += "\n"
        return f"{msg}<code>#updated {Utils.format_timestamp()}</code>"

    @staticmethod
    async def get_season_info():
        data = await Utils.fetch_json(Config.VAL_SEASON_URL) or {}
        season_data = data.get('data', [])
        if not season_data: return ""
        kst = timezone(timedelta(hours=9))
        offset = timedelta(hours=20, minutes=30)
        now = datetime.now(kst)
        future_dates = []
        for s in season_data:
            if s.get('endTime'):
                try:
                    dt = datetime.fromisoformat(s['endTime'].replace("Z", "+00:00")).astimezone(kst) + offset
                    if dt > now: future_dates.append(dt)
                except: continue
        if future_dates:
            target = min(future_dates)
            rem = target - now
            return f"시즌 종료까지: {rem.days}일 {rem.seconds//3600}시간 남음 (<code>{target.strftime('%Y-%m-%d')}</code> 종료)\n"
        return "<b>예정된 시즌 종료일이 없습니다.</b>"

    @staticmethod
    async def get_player_stats(name, tag):
        headers = {"Authorization": Config.HENRIK_API_KEY, "Accept": "*/*"}
        acc = await Utils.fetch_json(f"https://api.henrikdev.xyz/valorant/v1/account/{name}/{tag}", headers) or {}
        acc_data = acc.get('data', {})
        if not acc_data: return f"❌ 계정({name}#{tag})을 찾을 수 없습니다."
        puuid, region = acc_data.get('puuid'), acc_data.get('region', 'kr')
        tier_data = await Utils.fetch_json(f"https://api.henrikdev.xyz/valorant/v3/by-puuid/mmr/{region}/pc/{puuid}", headers) or {}
        curr_info = tier_data.get('data', {}).get('current', {})
        tier_str = curr_info.get('tier', {}).get('name', 'None')
        curr_rr = curr_info.get('rr', 'None')
        mmr_hist = await Utils.fetch_json(f"https://api.henrikdev.xyz/valorant/v2/by-puuid/mmr-history/{region}/pc/{puuid}", headers) or {}
        mmr_map = {i['match_id']: i.get('last_change', 0) for i in mmr_hist.get('data', {}).get('history', [])}
        matches = await Utils.fetch_json(f"https://api.henrikdev.xyz/valorant/v3/matches/{region}/{name}/{tag}", headers, {"mode": "competitive", "size": 10}) or {}
        match_list = matches.get('data', [])
        if not match_list: return f"❌ {name}#{tag}의 최근 전적이 없습니다."
        lines, tk, td, ts, tr = [], 0, 0, 0, 0
        for m in match_list:
            meta = m.get('metadata')
            if not meta or meta.get('game_start', 0) == 0: continue
            m_time = datetime.fromtimestamp(meta['game_start'], tz=pytz.timezone('Asia/Seoul'))
            date_str = m_time.strftime("%m.%d %I:%M%p").lower()
            me = next((p for p in m.get('players', {}).get('all_players', []) if p['puuid'] == puuid), None)
            if not me: continue
            st = me.get('stats', {})
            tk += st.get('kills', 0); td += st.get('deaths', 0); ts += st.get('score', 0); tr += meta.get('rounds_played', 1)
            teams = m.get('teams', {})
            if me['team'].lower() in teams:
                tm = teams[me['team'].lower()]
                res = "승리" if tm.get('has_won') else ("무승부" if tm.get('rounds_won') == tm.get('rounds_lost') else "패배")
                rr = mmr_map.get(meta.get('matchid'), 0)
                rr_str = f"+{rr}" if rr > 0 else str(rr)
                lines.append(f"{res}  [{st.get('kills')}/{st.get('deaths')}/{st.get('assists')}]  {meta.get('map')}  ({date_str})  <code>{rr_str}</code>")
        kd = tk / td if td else tk
        acs = int(ts / tr) if tr else 0
        url = f"https://tracker.gg/valorant/profile/riot/{urllib.parse.quote(name)}%23{urllib.parse.quote(tag)}/overview"
        msg = f"🐿️ <b><a href='{url}'>{name}#{tag}</a> 최근 10판!</b>\n서버 : {region}\nK/D : <b>{kd:.2f}</b>  |  ACS : <b>{acs}</b>\n현재티어 : <b>{tier_str},  {curr_rr}</b>\n"
        msg += "----------------------------------------------\n<pre>" + "\n".join(lines) + "</pre>\n"
        season = await ValorantService.get_season_info()
        return msg + season + f"\n<code>#updated {Utils.format_timestamp()}</code>"

class LolService:
    @staticmethod
    async def get_matches_message():
        headers = {"x-api-key": Config.LOL_API_KEY}
        matches = []
        now_kst = Utils.get_kst_now()
        today_date = now_kst.date()
        start_of_today = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        limit_date = now_kst + timedelta(days=10)
        async with aiohttp.ClientSession() as session:
            for lname, lid in Config.LOL_LEAGUES.items():
                url = f"https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US&leagueId={lid}"
                data = await Utils.fetch_json(url, headers) or {}
                schedule = data.get('data', {}).get('schedule', {}).get('events', [])
                for evt in schedule:
                    if not evt.get('startTime'): continue
                    try:
                        utc = datetime.fromisoformat(evt['startTime'].replace('Z', '+00:00')).replace(tzinfo=pytz.utc)
                        kst_match = utc.astimezone(pytz.timezone('Asia/Seoul'))
                        if start_of_today < kst_match < limit_date:
                            teams = evt.get('match', {}).get('teams', [])
                            if len(teams) >= 2:
                                t1, t2 = teams[0].get('code'), teams[1].get('code')
                                if t1 != "TBD" and t2 != "TBD":
                                    is_today = (kst_match.date() == today_date)
                                    matches.append((kst_match, lname, f"{t1} vs {t2}", evt['match']['strategy']['count'], is_today))
                    except: continue
        if not matches: return "⚔️ <b>예정된 경기가 없습니다.</b>"
        matches.sort()
        msg, cur_league = "", ""
        for m_time, league, title, bo, is_today in matches:
            d_name = f"{league} {now_kst.year}"
            if d_name != cur_league:
                if cur_league: msg += "\n"
                msg += f"<b>[{d_name}]</b>\n"
                cur_league = d_name
            time_str = m_time.strftime('%m.%d %H:%M')
            line = f"{title} <b>(Bo{bo})</b> <i>({time_str})</i>"
            if is_today: line = f"<u>{line}</u>"
            msg += line + "\n"
        return f"{msg}\n<code>#updated {Utils.format_timestamp()}</code>"

# ================ [메인 봇 및 핸들러] ================
intents = discord.Intents.default(); intents.message_content = True; intents.members = True; intents.voice_states = True
client = discord.Client(intents=intents); tree = app_commands.CommandTree(client)
telegram_app = None; telegram_chats = {"chats": {}}

def save_chats():
    with open(Config.TELEGRAM_CHATS_FILE, 'w', encoding='utf-8') as f: json.dump(telegram_chats, f, ensure_ascii=False, indent=4)
def load_chats():
    try:
        with open(Config.TELEGRAM_CHATS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"chats": {}}

# 텔레그램 핸들러
async def tg_register(update):
    if update.effective_chat:
        cid = str(update.effective_chat.id); name = update.effective_chat.title or update.effective_chat.first_name or '개인 채팅'
        if cid not in telegram_chats["chats"] or telegram_chats["chats"][cid]['name'] != name:
            telegram_chats["chats"][cid] = {'name': name}; save_chats()

async def cmd_help(update, context):
    """텔레그램 도움말"""
    await tg_register(update)
    help_text = (
        "📖 <b>봇 명령어 안내</b>\n\n"
        "/val - 발로란트 대회 일정\n"
        "/vct - VCT 대진표 이미지 조회\n"
        "/lol - 롤 대회 일정 조회\n"
        "/stat [닉네임#태그] - 발로란트 전적 검색\n"
    )
    await context.bot.send_message(update.effective_chat.id, help_text, parse_mode='HTML')

async def cmd_vct(update, context):
    await tg_register(update)
    keyboard = [
        [InlineKeyboardButton("Pacific", callback_data="vct_Pacific"), InlineKeyboardButton("Americas", callback_data="vct_Americas")],
        [InlineKeyboardButton("EMEA", callback_data="vct_EMEA"), InlineKeyboardButton("China", callback_data="vct_China")],
        [InlineKeyboardButton("Masters/Champions", callback_data="vct_Masters/Champions")]
    ]
    await context.bot.send_message(update.effective_chat.id, "🏆 VCT 대진표 조회\n현재 시즌의 대진표를 가져옵니다.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def cmd_val(update, context):
    await tg_register(update); await context.bot.send_message(update.effective_chat.id, await ValorantService.get_matches_message(), parse_mode='HTML', disable_web_page_preview=True)

async def cmd_lol(update, context):
    await tg_register(update); await context.bot.send_message(update.effective_chat.id, await LolService.get_matches_message(), parse_mode='HTML', disable_web_page_preview=True)

async def cmd_stat(update, context):
    await tg_register(update)
    if not context.args: return await context.bot.send_message(update.effective_chat.id, "❌ /stat lissa#vlr")
    try:
        name, tag = context.args[0].split('#')
        msg = await context.bot.send_message(update.effective_chat.id, f"🔍 <b>{name}#{tag}</b> 검색 중...", parse_mode='HTML')
        res = await ValorantService.get_player_stats(name, tag)
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=res, parse_mode='HTML', disable_web_page_preview=True)
    except:
        await context.bot.send_message(update.effective_chat.id, "❌ 형식: /stat 사용자#태그")

async def on_callback(update, context):
    query = update.callback_query; await query.answer()
    # refresh 관련 로직 삭제됨
    if query.data.startswith('vct_'):
        region = query.data.replace('vct_', '')
        league_path = ValorantService.get_current_league_path(region)
        status_msg = await query.message.reply_text(f"⏳ <b>{region}</b> 대진표 생성 중...\n", parse_mode='HTML')
        
        photo = await ValorantService.capture_bracket(league_path)
        if photo:
            wiki_url = f"https://liquipedia.net/valorant/{league_path}"
            caption_text = f"📊 <b><a href='{wiki_url}'>{region} 현재 대진표</a></b>"
            await query.message.reply_photo(
                photo=photo, 
                caption=caption_text, 
                parse_mode='HTML'
            )
            
        else:
            await query.message.reply_text("❌ 대진표를 가져오지 못했습니다.")
        await status_msg.delete()

# 디스코드 명령어
@tree.command(name="stat", description="발로란트 유저 전적 및 티어 조회")
@app_commands.describe(player="닉네임#태그 형식으로 입력 (예: lissa#vlr)")
async def discord_stat(interaction: discord.Interaction, player: str):
    await interaction.response.defer()
    try:
        if '#' not in player:
            await interaction.followup.send("❌ 형식: 닉네임#태그 (예: lissa#vlr)")
            return
        name, tag = player.split('#')
        res_html = await ValorantService.get_player_stats(name, tag)
        await interaction.followup.send(Utils.html_to_discord(res_html))
    except Exception as e:
        await interaction.followup.send(f"❌ 오류 발생: {e}")

async def setup_telegram_bot():
    global telegram_app, telegram_chats; telegram_chats = load_chats()
    telegram_app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    await telegram_app.initialize(); await telegram_app.start(); await telegram_app.updater.start_polling(drop_pending_updates=True)
    telegram_app.add_handler(CommandHandler('help', cmd_help))
    # /online 핸들러 삭제됨
    telegram_app.add_handler(CommandHandler('val', cmd_val))
    telegram_app.add_handler(CommandHandler('vct', cmd_vct))
    telegram_app.add_handler(CommandHandler('lol', cmd_lol))
    telegram_app.add_handler(CommandHandler('stat', cmd_stat))
    telegram_app.add_handler(CallbackQueryHandler(on_callback))
    print('Telegram Bot Started')

@client.event
async def on_ready():
    print(f'{client.user} 연결 성공!')
    try:
        # await tree.sync() 
        print("명령어 동기화 완료 (또는 스킵됨)")
    except Exception as e:
        print(f"동기화 오류: {e}")

    if not telegram_app: 
        await setup_telegram_bot()

if __name__ == "__main__":
    client.run(Config.DISCORD_TOKEN)