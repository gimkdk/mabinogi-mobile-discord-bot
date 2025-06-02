import discord
from discord.commands import slash_command
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from cogs.glass_raid_view import GlassRaidView
from cogs.abyss_view import AbyssView

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Supabase 클라이언트 초기화
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
if SUPABASE_URL is None or SUPABASE_KEY is None:
    raise ValueError("SUPABASE_URL 또는 SUPABASE_KEY 환경변수가 설정되지 않았습니다.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Intents 설정
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # 슬래시 커맨드 등록을 위해 필요함

# discord.Bot 객체 생성 (슬래시 커맨드용)
bot = discord.Bot(intents=intents)

# Cog 로드
bot.load_extension('cogs.glass_raid')
bot.load_extension('cogs.abyss')

GUILD_ID = os.getenv('TARGET_GUILD_ID')
if GUILD_ID is None:
     raise ValueError("TARGET_GUILD_ID 환경변수가 설정되지 않았습니다.")

# Glass Raid Channel ID
GLASS_RAID_CHANNEL_ID_STR = os.getenv('GLASS_RAID_CHANNEL_ID')
if GLASS_RAID_CHANNEL_ID_STR is None:
    raise ValueError("GLASS_RAID_CHANNEL_ID 환경변수가 설정되지 않았습니다.")
GLASS_RAID_CHANNEL_ID = int(GLASS_RAID_CHANNEL_ID_STR)

# Abyss Channel ID
ABYSS_CHANNEL_ID_STR = os.getenv('ABYSS_CHANNEL_ID')
if ABYSS_CHANNEL_ID_STR is None:
    raise ValueError("ABYSS_CHANNEL_ID 환경변수가 설정되지 않았습니다.")
ABYSS_CHANNEL_ID = int(ABYSS_CHANNEL_ID_STR)


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user} ({bot.user.id})')
    print('✅ 슬래시 커맨드가 준비되었습니다.')
    
    # ✅ 기존 모집글 View 재등록
    recruitments = supabase.table('recruitments').select('*').execute().data
    for r in recruitments:
        try:
            thread = await bot.fetch_channel(int(r['thread_id']))
            print(thread)
            print(f"[DEBUG] 스레드 ID {r['thread_id']} 가져오기 성공")

            if not isinstance(thread, discord.Thread):
                print(f"⚠️ ID {r['thread_id']}는 스레드가 아닙니다.")
                continue
            
            first_message_id = int(r['message_id'])
            message = await thread.fetch_message(first_message_id)
            print(message)

            channel_id = int(r['channel_id'])

            # Glass Raid Channel ID
            if channel_id == GLASS_RAID_CHANNEL_ID:
                view = GlassRaidView(supabase, r['id'], int(r['thread_id']), int(r['message_id']), bot)
            elif channel_id == ABYSS_CHANNEL_ID:
                view = AbyssView(supabase, r['id'], int(r['thread_id']), int(r['message_id']), bot)
            else:
                print(f"❓ 알 수 없는 channel_id: {channel_id}")
                continue
            view.message = message
            bot.add_view(view)
            print(f"✅ View 등록: recruitment_id={r['id']}")

        except discord.NotFound:
            print(f"❌ View 등록 실패: recruitment_id={r['id']} - 채널(스레드) 없음 (삭제됐거나 봇이 접근 불가)")
        except discord.Forbidden:
            print(f"❌ View 등록 실패: recruitment_id={r['id']} - 접근 권한 없음")
        except discord.HTTPException as e:
            print(f"❌ View 등록 실패: recruitment_id={r['id']} - HTTP 오류: {e}")
        except Exception as e:
            print(f"❌ View 등록 실패: recruitment_id={r['id']} - 기타 오류: {e}")

    await bot.sync_commands(force=True)

# 봇 실행
bot.run(DISCORD_TOKEN)