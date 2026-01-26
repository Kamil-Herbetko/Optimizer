import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv

from music import MusicPlayer, yt_source
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


@bot.tree.command(name="play")
async def play(interaction: discord.Interaction, query: str):
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

    for track in tracks:
        source, title = await yt_source(track)
        await player.add(source)

    await interaction.followup.send(f"🎶 Added {len(tracks)} track(s) to queue")


@bot.tree.command(name="skip")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭ Skipped")


@bot.tree.command(name="stop")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        vc.stop()
        await interaction.response.send_message("⏹ Stopped")


@bot.tree.command(name="leave")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("👋 Disconnected")


@tasks.loop(minutes=2)
async def auto_disconnect():
    for vc in bot.voice_clients:
        if not vc.is_playing() and len(vc.channel.members) == 1:
            await vc.disconnect()


@bot.tree.command(name="volume")
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


bot.run(os.getenv("DISCORD_TOKEN"))
