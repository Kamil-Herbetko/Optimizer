import asyncio
import discord
import yt_dlp

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class MusicPlayer:
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.voice = None
        self.current = None

        bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        while True:
            self.next.clear()
            self.current = await self.queue.get()

            self.voice.play(
                self.current,
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set),
            )

            await self.next.wait()

    async def add(self, source):
        await self.queue.put(source)


async def yt_source(query: str):
    loop = asyncio.get_event_loop()

    def extract():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]
            return info["url"], info["title"]

    url, title = await loop.run_in_executor(None, extract)
    return discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), title
