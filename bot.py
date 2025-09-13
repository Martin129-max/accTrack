import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

ACCOUNTS_FILE = "accounts.json"
STATE_FILE = "state.json"

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- LOAD / SAVE ---
def load_accounts():
    with open(ACCOUNTS_FILE, "r") as f:
        return json.load(f)

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)

# --- !status COMMAND ---
@bot.command()
async def status(ctx):
    accounts = load_accounts()

    header = f"{'Account':<12} {'Status':<12} {'Dailies':<8} {'User':<15}\n"
    rows = []
    for acc in accounts:
        dailies = "✅" if acc["dailies"] == "Done" else "❌"
        status = acc["status"]
        user = acc["user"] if acc["user"] else "-"
        rows.append(f"{acc['username']:<12} {status:<12} {dailies:<8} {user:<15}")

    table = "```\n" + header + "\n".join(rows) + "\n```"
    embed = discord.Embed(title="📊 Account Status", description=table, color=0x00ff00)
    await ctx.send(embed=embed)

# --- Account Update View ---
class AccountView(View):
    def __init__(self, acc, accounts):
        super().__init__(timeout=None)
        self.acc = acc
        self.accounts = accounts

        # Dailies button
        self.dailies_btn = Button(
            label=f"Dailies: {'✅' if acc['dailies']=='Done' else '❌'}",
            style=discord.ButtonStyle.primary
        )
        self.dailies_btn.callback = self.dailies_callback
        self.add_item(self.dailies_btn)

        # Use/Release button
        self.use_btn = Button(
            label=f"{'Release' if acc['status']=='In Use' else 'Use'}",
            style=discord.ButtonStyle.success if acc['status']=='Available' else discord.ButtonStyle.danger
        )
        self.use_btn.callback = self.use_callback
        self.add_item(self.use_btn)

        # Ultra bosses multi-select
        ultra_options = []
        for boss, status in acc.get("ultra_bosses", {}).items():
            ultra_options.append(discord.SelectOption(label=boss, default=(status == "Done")))
        self.ultra_select = Select(
            placeholder="Select Ultra Bosses Done",
            options=ultra_options,
            min_values=0,
            max_values=len(ultra_options)
        )
        self.ultra_select.callback = self.ultra_callback
        self.add_item(self.ultra_select)

    async def dailies_callback(self, interaction: discord.Interaction):
        self.acc["dailies"] = "Done" if self.acc["dailies"] == "Not Done" else "Not Done"
        save_accounts(self.accounts)
        self.dailies_btn.label = f"Dailies: {'✅' if self.acc['dailies']=='Done' else '❌'}"
        await interaction.response.edit_message(view=self)

    async def use_callback(self, interaction: discord.Interaction):
        if self.acc["status"] == "Available":
            self.acc["status"] = "In Use"
            self.acc["user"] = interaction.user.name
        else:
            self.acc["status"] = "Available"
            self.acc["user"] = ""
        save_accounts(self.accounts)
        self.use_btn.label = f"{'Release' if self.acc['status']=='In Use' else 'Use'}"
        await interaction.response.edit_message(view=self)

    async def ultra_callback(self, interaction: discord.Interaction):
        selected = self.ultra_select.values
        for boss in self.acc["ultra_bosses"]:
            self.acc["ultra_bosses"][boss] = "Done" if boss in selected else "Not Done"
        save_accounts(self.accounts)
        await interaction.response.edit_message(view=self)

# --- !accounts COMMAND ---
@bot.command()
async def accounts(ctx):
    accounts = load_accounts()
    for acc in accounts:
        ultra_str = ", ".join([f"{boss}:{'✅' if status=='Done' else '❌'}" for boss, status in acc["ultra_bosses"].items()])
        desc = f"**Status:** {acc['status']}\n**User:** {acc['user'] if acc['user'] else '-'}\n**Dailies:** {'✅' if acc['dailies']=='Done' else '❌'}\n**Ultras:** {ultra_str}"
        embed = discord.Embed(title=f"⚙️ {acc['username']}", description=desc, color=0x3498db)
        await ctx.send(embed=embed, view=AccountView(acc, accounts))

# --- !ultras COMMAND ---
@bot.command()
async def ultras(ctx):
    accounts = load_accounts()

    bosses = {}
    for acc in accounts:
        for boss, status in acc["ultra_bosses"].items():
            if boss not in bosses:
                bosses[boss] = []
            if status == "Not Done":
                bosses[boss].append(acc["username"])

    desc = ""
    for boss, accs in bosses.items():
        if accs:
            desc += f"**{boss} ❌**: {', '.join(accs)}\n"
        else:
            desc += f"**{boss} ✅**: All done\n"

    embed = discord.Embed(title="💀 Ultra Boss Progress", description=desc, color=0xff0000)
    await ctx.send(embed=embed)

# --- STARTUP ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)
