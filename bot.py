import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv

from music import MusicPlayer
from spotify import spotify_to_search

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

players = {}


def get_player(guild):
    if guild.id not in players:
        players[guild.id] = MusicPlayer(bot, guild)
    return players[guild.id]


@bot.event
async def on_ready():
    await bot.tree.sync()
    auto_disconnect.start()
    print(f"Logged in as {bot.user}")


@bot.tree.command(name="help", description="Show all commands and how to use them")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Available commands**\n"
        "/help — Show this command guide.\n"
        "/play query:<song name or Spotify song/playlist URL> loop:<true/false> "
        "— Join your voice channel and queue music. Loop defaults to false; "
        "true repeats a song or every playlist track in order.\n"
        "/skip — Skip the current track (looping tracks return on the next cycle).\n"
        "/stop — Stop playback and clear the queue, including loops.\n"
        "/leave — Stop playback, clear the queue, and disconnect.\n"
        "/volume level:<0–200> — Set playback volume as a percentage.\n\n"
        "**Examples**\n"
        "/play query:Never Gonna Give You Up loop:true\n"
        "/play query:https://open.spotify.com/playlist/... loop:true\n"
        "/volume level:75",
        ephemeral=True,
    )


@bot.tree.command(name="play", description="Play a song or Spotify playlist, optionally on repeat")
@discord.app_commands.describe(query="Song name or Spotify song/playlist URL", loop="Repeat queued tracks in order (default: false)")
async def play(interaction: discord.Interaction, query: str, loop: bool = False):
    await interaction.response.defer()

    if not interaction.user.voice:
        return await interaction.followup.send("Join a voice channel first.")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    player = get_player(interaction.guild)
    player.voice = vc

    if "spotify.com" in query:
        tracks = spotify_to_search(query)
    else:
        tracks = [query]

    if not tracks:
        return await interaction.followup.send("No tracks found. Use a song name or Spotify song/playlist URL.")
    await player.add(tracks, loop=loop)

    await interaction.followup.send(f"🎶 Added {len(tracks)} track(s) to queue" + (" (loop enabled)" if loop else ""))


@bot.tree.command(name="skip", description="Skip the current track")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭ Skipped")
    else:
        await interaction.response.send_message("Nothing is playing.")


@bot.tree.command(name="stop", description="Stop playback and clear the queue and loops")
async def stop(interaction: discord.Interaction):
    get_player(interaction.guild).stop()
    await interaction.response.send_message("⏹ Stopped and cleared the queue")


@bot.tree.command(name="leave", description="Stop playback and disconnect from voice")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        get_player(interaction.guild).stop()
        await vc.disconnect()
        await interaction.response.send_message("👋 Disconnected")
    else:
        await interaction.response.send_message("Not connected to a voice channel.")


@tasks.loop(minutes=2)
async def auto_disconnect():
    for vc in bot.voice_clients:
        if not vc.is_playing() and len(vc.channel.members) == 1:
            get_player(vc.guild).stop()
            await vc.disconnect()


@bot.tree.command(name="volume", description="Set playback volume from 0 to 200 percent")
async def volume(interaction: discord.Interaction, level: int):
    """
    Set playback volume (0–200)
    """
    if level < 0 or level > 200:
        return await interaction.response.send_message(
            "Volume must be between 0 and 200"
        )

    player = get_player(interaction.guild)
    player.volume = level / 100

    vc = interaction.guild.voice_client
    if vc and vc.source:
        vc.source.volume = player.volume

    await interaction.response.send_message(f"🔊 Volume set to {level}%")


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
