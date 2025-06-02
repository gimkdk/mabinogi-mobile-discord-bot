import discord
from discord.ui import Button, View
from discord import Interaction

class AbyssView(View):
    def __init__(self, supabase_client, recruitment_id, thread_id, message_id, bot):
        super().__init__(timeout=None)  # timeout=None으로 무제한 활성화 유지
        self.supabase = supabase_client
        self.recruitment_id = recruitment_id
        self.thread_id = thread_id
        self.bot = bot
        self.message_id = message_id
        self.message = None

    async def init_message(self):
        try:
            thread = await self.bot.fetch_channel(self.thread_id)
            self.message = await thread.fetch_message(self.message_id)
        except Exception as e:
            print(f"스레드 메시지 가져오기 실패: {e}")

        # ✅ persistent View에 custom_id 지정된 버튼 추가
    async def fetch_message(self):
        # 메시지 객체를 fetch해서 self.message에 저장
        if self.message is None:
            try:
                thread = await self.bot.fetch_channel(self.thread_id)  # 스레드 채널 fetch
                self.message = await thread.fetch_message(self.message_id)  # 메시지 fetch
            except Exception as e:
                print(f"스레드 메시지 가져오기 실패: {e}")

    async def update_embed(self):
        # 현재 참여자 목록을 DB에서 가져오기
        if self.message is None:
            await self.fetch_message()
        try:
            recruitment_res = self.supabase.table('recruitments')\
                .select('*')\
                .eq('id', self.recruitment_id)\
                .execute()

            recruitment = recruitment_res.data[0]

            participants_res = self.supabase.table('participants')\
                .select('discord_id')\
                .eq('recruitment_id', self.recruitment_id)\
                .execute()
            participants = participants_res.data or []

            max_participants = recruitment.get('max_participants', 0)
            difficulty = recruitment.get('difficulty', '정보없음')
            leader_id = int(recruitment.get('leader_discord_id'))
            start_datetime = recruitment.get('start_datetime', '출발시간 없음')
            message_description = recruitment.get('message_description', '비고없음')
            abyss_kind = recruitment.get('abyss_kind', "어비스 종류 없음")

            # 참여자 멘션 문자열 생성
            if participants:
                mentions = "\n".join([f"• <@{p['discord_id']}>" for p in participants])
            else:
                mentions = "• 아직없음"

            # 지원자 수
            current_count = len(participants)

            embed = discord.Embed(
                title=f"📢 어비스 {abyss_kind}({difficulty}) 모집!",
                description=f"🕓 출발시간: {start_datetime}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🔰 난이도", value=f"```{difficulty}```", inline=True)
            embed.add_field(name="모집인원", value=f"```{current_count} / {max_participants}```", inline=True)
            embed.add_field(name="\n", value="\n", inline=False)
            embed.add_field(name="", value="--------", inline=False)
            embed.add_field(name="👑 파티장", value=f"<@{leader_id}>", inline=True)
            embed.add_field(name="🙋 지원자 목록", value=mentions, inline=True)
            embed.add_field(name="\n", value="\n", inline=False)
            embed.add_field(name="--------", value="\n", inline=False)
            embed.add_field(name="❗ 참고 사항", value=f"\n{message_description}", inline=False)
            embed.set_thumbnail(url="https://i.namu.wiki/i/KsstyV_JvUrKjIK1E3PSfg5stY7S-a-VD9EMPp9uJCIM1DHz7mGuCqeNSg9Bsd1rEMGgkGSfyNyUifA4QbymBQ.webp")

            if self.message is not None:
                await self.message.edit(embed=embed, view=self)
            else:
                print("Error: self.message is None, embed를 업데이트할 수 없습니다.")   

        except Exception as e:
            print(f"Embed 업데이트 실패: {e}")

    @discord.ui.button(label="지원하기", style=discord.ButtonStyle.green, custom_id="apply_abyss_button")
    async def apply_abyss_button(self, button: Button, interaction: Interaction):
        user_id = str(interaction.user.id)
        try:
            # 이미 지원했는지 확인
            check = self.supabase.table('participants')\
                .select('*')\
                .eq('recruitment_id', self.recruitment_id)\
                .eq('discord_id', user_id)\
                .execute()
            if check.data and len(check.data) > 0:
                await interaction.response.send_message("이미 지원하셨습니다!", ephemeral=True)
                return
             # 지원 인원 초과 여부 체크
            recruitment_res = self.supabase.table('recruitments')\
                .select('max_participants')\
                .eq('id', self.recruitment_id)\
                .execute()

            max_participants = recruitment_res.data[0]['max_participants']

            participants_res = self.supabase.table('participants')\
                .select('*')\
                .eq('recruitment_id', self.recruitment_id)\
                .execute()

            current_count = len(participants_res.data)

            if current_count >= max_participants:
                await interaction.response.send_message("모집인원이 꽉 찼습니다!", ephemeral=True)
                return
            
            # 지원자 등록
            res = self.supabase.table('participants').insert({
                'recruitment_id': self.recruitment_id,
                'discord_id': user_id
            }).execute()

            if res.data:
                await interaction.response.send_message("지원 완료!", ephemeral=True)
                await self.update_embed()
                print(res.data)
            else:
                await interaction.response.send_message("지원 중 오류가 발생했습니다.", ephemeral=True)
        except Exception as e:
            print(f"지원하기 오류: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("지원 중 오류가 발생했습니다.", ephemeral=True)

    @discord.ui.button(label="지원취소", style=discord.ButtonStyle.red, custom_id="cancel_abyss_button")
    async def cancel_abyss_button(self, button: Button, interaction: Interaction):
        user_id = str(interaction.user.id)
        try:
            # 지원 내역 삭제
            res = self.supabase.table('participants')\
                .delete()\
                .eq('recruitment_id', self.recruitment_id)\
                .eq('discord_id', user_id)\
                .execute()
            
            if res.data:
                await interaction.response.send_message("지원 취소 완료!", ephemeral=True)
                await self.update_embed()
                print(res.data)
            else:
                await interaction.response.send_message("지원 내역이 없습니다.", ephemeral=True)
        except Exception as e:
            print(f"지원취소 오류: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("취소 중 오류가 발생했습니다.", ephemeral=True)