# Optimizer
Very small discord music bot for self hosting.

Use `/help` in Discord to see all commands and usage examples.

| Command | Usage |
| --- | --- |
| `/help` | Show the command guide. |
| `/play query:<song name or Spotify song/playlist URL> loop:<true/false>` | Queue music; `loop` defaults to `false`. Set `loop:true` to repeat the song or playlist tracks in queue order. Join a voice channel first. |
| `/skip` | Skip the current track. Looping tracks return on the next cycle. |
| `/stop` | Stop playback and clear the queue, including loops. |
| `/leave` | Stop playback, clear the queue, and disconnect. |
| `/volume level:<0–200>` | Set playback volume as a percentage. |

For example: `/play query:Never Gonna Give You Up loop:true` or
`/play query:https://open.spotify.com/playlist/... loop:true`.

## YouTube authentication

The Python dependencies include Deno and yt-dlp's default extras (including
the EJS challenge solver) for YouTube's JavaScript challenges. Install or update
them locally with `uv sync --upgrade-package yt-dlp`, then run `uv run bot.py`
so Deno is on the bot's PATH. Docker installs these dependencies automatically.

For cookie-authenticated requests, the bot adds the `web_embedded` player client
alongside yt-dlp's defaults to work around the known
[“The page needs to be reloaded” issue](https://github.com/yt-dlp/yt-dlp/issues/17389).
If you already have a Docker image, rebuild it and recreate the container:

```sh
docker build --no-cache -t optimizer .
```

Then use the `docker run` command below with your existing cookie file.

If YouTube says “Sign in to confirm you’re not a bot”, the bot needs cookies
from a browser session that can play the video. Export YouTube cookies in
Mozilla/Netscape format following the
[yt-dlp YouTube cookie guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies),
save them as `cookies.txt`, and add this to `.env`:

```dotenv
YTDLP_COOKIE_FILE=/absolute/path/to/cookies.txt
```

Restart the bot. For a bot running on your desktop, you can instead set
`YTDLP_COOKIES_FROM_BROWSER=firefox` (or `chrome`) to read cookies from a local
browser. The cookie file takes precedence when both settings are present.
Browser extraction requires that browser's profile to be accessible to the bot;
use an exported file for Docker.

Build and run with a mounted cookie file:

```sh
docker build -t optimizer .
docker run --env-file .env \
  -e YTDLP_COOKIE_FILE=/cookies/cookies.txt \
  --mount type=bind,src="$(pwd)/cookies.txt",dst=/cookies/cookies.txt \
  optimizer
```

The mount must be writable because yt-dlp saves its cookie jar on exit.
Cookies are credentials: keep them private. `.gitignore` and `.dockerignore`
exclude `cookies*.txt`; store differently named cookie files outside this repo.
If authentication still fails, export fresh cookies and rebuild with
`docker build --no-cache -t optimizer .` to refresh yt-dlp. YouTube may also
block the server's IP, so cookies cannot guarantee access.

## Audio stream 403 errors

The bot checks audio candidates with yt-dlp until it finds a working format,
instead of probing every available audio and video format. It passes the
selected stream's HTTP headers and URL-scoped cookies to FFmpeg. This avoids
losing the request context when moving from extraction to playback. Rebuild
the image and recreate the container after updating the bot.

If 403 errors persist, test yt-dlp on the same host/container and with the same
cookies. YouTube can reject streams because of IP/session restrictions or
[PO token requirements](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide).
Passing headers cannot fix those server-side restrictions.
