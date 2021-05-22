import os

from discord.ext import commands
from discord.ext.commands.core import command

from discord_slash import SlashCommand # Importing the newly installed library.

client = commands.Bot(command_prefix=';')
slash = SlashCommand(client, sync_commands=True)

@client.event
async def on_ready():
    print("Ready!")

print("--- Loading Cogs ---")
for _, _, files in os.walk('cogs/'):
    for file in files:
        file_name, ext = os.path.splitext(file)
        if file_name.startswith('cog'):
            print(f"{file}")
            client.load_extension(f'cogs.{file_name}')

    break

print("--- Done Loading Cogs ---")

client.run(os.environ.get("TOKEN"))
