import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from music import MusicPlayer


class Voice:
    def __init__(self):
        self.after = None
        self.played = asyncio.Queue()

    def is_connected(self):
        return True

    def play(self, source, after):
        self.after = after
        self.played.put_nowait(source)

    def stop(self):
        if self.after:
            callback, self.after = self.after, None
            callback(None)


class MusicPlayerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.player = MusicPlayer(SimpleNamespace(loop=asyncio.get_running_loop()), None)
        self.player.voice = Voice()
        self.extract = AsyncMock(side_effect=lambda query: (query, query))
        self.patches = [
            patch("music.yt_source", self.extract),
            patch("music.discord.PCMVolumeTransformer", side_effect=lambda source, volume: source),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for item in self.patches:
            item.stop()

    async def next_track(self):
        return await asyncio.wait_for(self.player.voice.played.get(), timeout=1)

    async def test_playlist_repeats_in_order_with_fresh_sources(self):
        await self.player.add(["first", "second"], loop=True)
        for expected in ["first", "second", "first", "second"]:
            self.assertEqual(await self.next_track(), expected)
            self.player.voice.stop()
        self.assertEqual(self.extract.await_count, 4)
        self.player.stop()

    async def test_song_repeats(self):
        await self.player.add(["song"], loop=True)
        self.assertEqual(await self.next_track(), "song")
        self.player.voice.stop()
        self.assertEqual(await self.next_track(), "song")
        self.player.stop()

    async def test_default_does_not_repeat(self):
        await self.player.add(["song"])
        await self.next_track()
        self.player.voice.stop()
        await asyncio.wait_for(self.player.queue.join(), timeout=1)
        self.assertEqual(self.extract.await_count, 1)

    async def test_stop_clears_loop_and_pending_tracks(self):
        await self.player.add(["first", "second"], loop=True)
        await self.next_track()
        self.player.stop()
        await asyncio.wait_for(self.player.queue.join(), timeout=1)
        self.assertTrue(self.player.queue.empty())
        self.assertEqual(self.extract.await_count, 1)

    async def test_stop_during_extraction_discards_source(self):
        started, release = asyncio.Event(), asyncio.Event()
        source = SimpleNamespace(cleanup=unittest.mock.Mock())

        async def extract(query):
            started.set()
            await release.wait()
            return source, query

        self.extract.side_effect = extract
        await self.player.add(["song"], loop=True)
        await asyncio.wait_for(started.wait(), timeout=1)
        self.player.stop()
        release.set()
        await asyncio.wait_for(self.player.queue.join(), timeout=1)
        source.cleanup.assert_called_once()
        self.assertTrue(self.player.voice.played.empty())
