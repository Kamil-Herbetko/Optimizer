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
