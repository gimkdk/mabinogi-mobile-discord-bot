import discord
from discord.commands import slash_command, Option
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
from .glass_raid_view import GlassRaidView
import re

load_dotenv()  # .env 파일 로드해서 환경변수 등록

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


if SUPABASE_URL is None or SUPABASE_KEY is None:
    raise ValueError("SUPABASE_URL 또는 SUPABASE_KEY 환경변수가 설정되지 않았습니다.")

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

GUILD_ID = os.getenv('TARGET_GUILD_ID')
if GUILD_ID is None:
     raise ValueError("TARGET_GUILD_ID 환경변수가 설정되지 않았습니다.")

GLASS_RAID_CHANNEL_ID_STR = os.getenv('GLASS_RAID_CHANNEL_ID')
if GLASS_RAID_CHANNEL_ID_STR is None:
    raise ValueError("GLASS_RAID_CHANNEL_ID 환경변수가 설정되지 않았습니다.")
GLASS_RAID_CHANNEL_ID = int(GLASS_RAID_CHANNEL_ID_STR)

class GlassRaid(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="글라스기브넨등록", description="글라스 기브넨 모집 등록", guild_ids=[str(os.getenv('TARGET_GUILD_ID'))])
    async def register_glass(
        self, 
        ctx: discord.ApplicationContext,
        난이도=Option(str, "난이도를 입력하세요", choices=["입문", "어려움"]),
        모집인원=Option(int, "모집인원 수를 입력하세요", choices=[1, 2, 3, 4, 5, 6, 7]),
        출발시간=Option(str, "출발시간을 24시간 형식(예: 00:00)으로 입력하세요", required=True),
        메시지비고=Option(str, "메시지를 선택해주세요", choices=["시간 조율 가능해요", "출발시간까지만 모집합니다"], required=True),
    ):
        now_seoul = datetime.now(ZoneInfo("Asia/Seoul"))
        now_seoul_date = now_seoul.strftime("%m월 %d일")
        
        # 출발시간 형식 체크 (HH:mm)
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", str(출발시간)):
            await ctx.respond("❌ 출발시간은 24시간 형식(예: 00:00)이어야 합니다.", ephemeral=True)
            return
        allowed_channel_id = int(GLASS_RAID_CHANNEL_ID)  # 변경하세요

        if ctx.channel.id != allowed_channel_id:
            await ctx.respond("이 명령어는 지정된 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            thread = await ctx.channel.create_thread(
                name=f"모집날짜:{now_seoul_date}/글라스기브넨({난이도})/출발시간:{출발시간} - {ctx.author.display_name}",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440
            )
            print(f"스레드 생성됨: {thread.id}")
            
            data = {
                'thread_id': str(thread.id),
                'channel_id': str(ctx.channel.id),
                'leader_discord_id': str(ctx.author.id),
                'max_participants': 모집인원,
                'start_datetime': 출발시간,
                'message_description':메시지비고,
                'difficulty': 난이도,
            }

            res = supabase.table('recruitments').insert(data).execute()
            recruitment_id = res.data[0]['id']  # 여기서 ID 얻음
            
            embed = discord.Embed(
                title=f"📢 글라스기브넨({난이도}) 모집!",
                description=f"🕓 출발시간: {출발시간}",
                color=discord.Color.blue()
            )
            embed.add_field(name="🔰 난이도", value=f"```{난이도}```", inline=True)
            embed.add_field(name="모집 인원", value=f"```0 / {모집인원}```", inline=True)
            embed.add_field(name="\n", value="\n", inline=False)
            embed.add_field(name="", value="--------", inline=False)
            embed.add_field(name="👑 파티장", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="🙋 지원자 목록", value=f"• 아직없음", inline=True)
            embed.add_field(name="\n", value="\n", inline=False)
            embed.add_field(name="--------", value="\n", inline=False)
            embed.add_field(name="❗ 참고 사항", value=f"\n{메시지비고}", inline=False)
            

            embed.set_thumbnail(url="https://dszw1qtcnsa5e.cloudfront.net/community/20250326/d8fe4dce-de91-4cde-9bc0-43ce3ae99ed6/%EA%B8%80%EB%9D%BC%EC%8A%A4%EA%B8%B0%EB%B8%8C%EB%84%A8%EA%B3%BC%EC%9D%98%EC%A1%B0%EC%9A%B0.png")  # <-- 이미지 넣기

            msg = await thread.send(embed=embed)

            # 2) 메시지 ID DB에 업데이트
            update_res = supabase.table('recruitments')\
                .update({'message_id': str(msg.id)})\
                .eq('id', recruitment_id)\
                .execute()
            # 3) View에 메시지 객체도 넘겨서 embed 업데이트 가능하게 함
            view = GlassRaidView(supabase, recruitment_id, thread.id, msg.id, self.bot)
            await msg.edit(view=view)
            
            await ctx.respond("모집등록 완료", ephemeral=True)
        except Exception as e:
            print(f"스레드 생성 실패: {e}")
            await ctx.respond("스레드 생성 중 오류가 발생했습니다.", ephemeral=True)
            return

def setup(bot):
    bot.add_cog(GlassRaid(bot))