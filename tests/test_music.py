import asyncio
import unittest
import tempfile
import shlex
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from music import FFMPEG_OPTIONS, MusicPlayer, ffmpeg_options, ydl_options, yt_source


class YouTubeSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cookie_file_is_passed_to_extractor(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as cookies:
            with patch.dict("os.environ", {"YTDLP_COOKIE_FILE": cookies.name}, clear=True), \
                    patch("music.yt_dlp.YoutubeDL") as ydl, \
                    patch("music.discord.FFmpegPCMAudio") as audio:
                ydl.return_value.__enter__.return_value.extract_info.return_value = {
                    "entries": [{"url": "https://example.com/audio", "title": "Song"}]
                }
                ydl.return_value.__enter__.return_value.cookiejar.get_cookie_header.return_value = None
                source, title = await yt_source("song")
                self.assertEqual(ydl.call_args.args[0]["cookiefile"], cookies.name)
                self.assertEqual(
                    ydl.call_args.args[0]["extractor_args"]["youtube"]["player_client"],
                    ["default", "web_embedded"],
                )
                self.assertIs(source, audio.return_value)
                self.assertEqual(title, "Song")

    async def test_browser_cookies_are_passed_to_extractor(self):
        with patch.dict("os.environ", {"YTDLP_COOKIES_FROM_BROWSER": "firefox"}, clear=True), \
                patch("music.yt_dlp.YoutubeDL") as ydl, \
                patch("music.discord.FFmpegPCMAudio"):
            ydl.return_value.__enter__.return_value.extract_info.return_value = {
                "entries": [{"url": "https://example.com/audio", "title": "Song"}]
            }
            ydl.return_value.__enter__.return_value.cookiejar.get_cookie_header.return_value = None
            await yt_source("song")
            self.assertEqual(ydl.call_args.args[0]["cookiesfrombrowser"], ("firefox",))
            self.assertIn("web_embedded", ydl.call_args.args[0]["extractor_args"]["youtube"]["player_client"])

    def test_anonymous_requests_keep_default_clients(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertNotIn("extractor_args", ydl_options())

    async def test_ffmpeg_receives_stream_headers_and_only_scoped_cookies(self):
        with patch.dict("os.environ", {}, clear=True), \
                patch("music.yt_dlp.YoutubeDL") as ydl, \
                patch("music.discord.FFmpegPCMAudio") as audio:
            extractor = ydl.return_value.__enter__.return_value
            extractor.extract_info.return_value = {"entries": [{
                "url": "https://example.com/audio", "title": "Song",
                "http_headers": {"User-Agent": 'Browser "quoted" agent',
                                 "Referer": "https://www.youtube.com/", "Cookie": "unscoped=secret"},
            }]}
            extractor.cookiejar.get_cookie_header.return_value = "media=session"
            await yt_source("song")
            extractor.cookiejar.get_cookie_header.assert_called_once_with("https://example.com/audio")
            self.assertEqual(ydl.call_args.args[0]["check_formats"], "selected")
            args = shlex.split(audio.call_args.kwargs["before_options"])
            block = args[args.index("-headers") + 1]
            self.assertIn('User-Agent: Browser "quoted" agent\r\n', block)
            self.assertIn("Referer: https://www.youtube.com/\r\n", block)
            self.assertIn("Cookie: media=session\r\n", block)
            self.assertNotIn("unscoped", block)
            self.assertEqual(audio.call_args.args[0], "https://example.com/audio")

    def test_no_headers_keeps_reconnect_options(self):
        self.assertEqual(ffmpeg_options({}), FFMPEG_OPTIONS)

    def test_format_checks_stop_at_first_working_audio(self):
        import yt_dlp

        formats = [
            {"format_id": "low-audio", "vcodec": "none", "acodec": "opus"},
            {"format_id": "good-audio", "vcodec": "none", "acodec": "opus"},
            {"format_id": "blocked-audio", "vcodec": "none", "acodec": "opus"},
            {"format_id": "video", "vcodec": "av1", "acodec": "none"},
        ]
        checked = []

        def check(candidates):
            for candidate in candidates:
                checked.append(candidate["format_id"])
                if candidate["format_id"] != "blocked-audio":
                    yield candidate

        with patch.dict("os.environ", {}, clear=True):
            with yt_dlp.YoutubeDL(ydl_options()) as ydl:
                with patch.object(ydl, "_check_formats", side_effect=check):
                    selected = ydl._select_formats(formats, ydl.build_format_selector(ydl.params["format"]))
        self.assertEqual([item["format_id"] for item in selected], ["good-audio"])
        self.assertEqual(checked, ["blocked-audio", "good-audio"])

    def test_headers_cannot_inject_newlines(self):
        with self.assertRaisesRegex(ValueError, "newline"):
            ffmpeg_options({"User-Agent": "browser\r\nInjected: value"})

    async def test_reload_failure_has_update_instructions_without_retrying(self):
        import yt_dlp

        with patch.dict("os.environ", {}, clear=True), \
                patch("music.yt_dlp.YoutubeDL") as ydl, \
                patch("music.discord.FFmpegPCMAudio") as audio:
            extract = ydl.return_value.__enter__.return_value.extract_info
            extract.side_effect = yt_dlp.utils.DownloadError("The page needs to be reloaded.")
            with self.assertRaisesRegex(RuntimeError, "embedded-client workaround"):
                await yt_source("song")
            extract.assert_called_once()
            audio.assert_not_called()

    async def test_missing_cookie_file_fails_before_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"YTDLP_COOKIE_FILE": f"{directory}/missing.txt"}, clear=True), \
                    patch("music.yt_dlp.YoutubeDL") as ydl:
                with self.assertRaisesRegex(ValueError, "YTDLP_COOKIE_FILE"):
                    await yt_source("song")
                ydl.assert_not_called()

    async def test_bot_challenge_explains_authentication_setup(self):
        import yt_dlp

        with patch.dict("os.environ", {}, clear=True), \
                patch("music.yt_dlp.YoutubeDL") as ydl, \
                patch("music.discord.FFmpegPCMAudio") as audio:
            ydl.return_value.__enter__.return_value.extract_info.side_effect = (
                yt_dlp.utils.DownloadError("Sign in to confirm you’re not a bot")
            )
            with self.assertRaisesRegex(RuntimeError, "YTDLP_COOKIE_FILE"):
                await yt_source("song")
            audio.assert_not_called()


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
