import asyncio
import logging
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
        self.volume = 0.5
        self.generation = 0

        bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        while True:
            self.next.clear()
            query, repeat = await self.queue.get()
            generation = self.generation
            try:
                # FFmpeg sources are consumed and cleaned up after playback.
                # Resolve a fresh source on every pass through the queue.
                source, _ = await yt_source(query)
                if generation != self.generation or not self.voice or not self.voice.is_connected():
                    source.cleanup()
                    continue
                self.current = source
                self.voice.play(
                    discord.PCMVolumeTransformer(source, volume=self.volume),
                    after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set),
                )
                await self.next.wait()
                if repeat and generation == self.generation:
                    self.queue.put_nowait((query, repeat))
            except Exception:
                logging.exception("Could not play %s", query)
            finally:
                self.current = None
                self.queue.task_done()

    async def add(self, queries, loop=False):
        for query in queries:
            self.queue.put_nowait((query, loop))

    def stop(self):
        self.generation += 1
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()
        if self.voice:
            self.voice.stop()


async def yt_source(query: str):
    loop = asyncio.get_event_loop()

    def extract():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]
            return info["url"], info["title"]

    url, title = await loop.run_in_executor(None, extract)
    return discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), title
