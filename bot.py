import discord
from discord.ext import commands
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import os
import re
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Load model + tokenizer
model = AutoModelForSequenceClassification.from_pretrained("discord_scam_model")
tokenizer = AutoTokenizer.from_pretrained("discord_scam_model")
model.eval()

# Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disable default help

# Store original message data (key: review_message_id, value: original message data)
pending_reviews = {}

# -------------------------------
# CONFIG SECTION
# -------------------------------

ALLOWED_DOMAINS = {
    "youtube.com", "youtu.be",
    "deviantart.com",
    "discord.com", "discord.gg",
    "github.com",
}

MOD_REVIEW_CHANNEL_ID = None  # Will be set by admin using !reviewchannel command

# -------------------------------
# URL Extraction Helper
# -------------------------------

def extract_domains(text):
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    domains = []
    for url in urls:
        try:
            domain = url.split("/")[2].lower()
            domains.append(domain)
        except:
            pass
    return domains

# -------------------------------
# Prediction Function
# -------------------------------

def predict(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        pred = torch.argmax(logits).item()
        confidence = probs[0][pred].item()
    is_spam = (pred == 1)
    return is_spam, confidence

# -------------------------------
# COMMANDS
# -------------------------------

@bot.command(name="help")
async def help_command(ctx):
    """Display help menu"""
    help_text = (
        "🦸 **SentriBot Help Menu**\n\n"
        "**Commands:**\n"
        "• `!help` - Display this help menu\n"
        "• `!reviewchannel <channel_id>` - **(Admin only)** Set the moderation review channel\n\n"
        "**Features:**\n"
        "• Automatically detects spam and phishing messages using AI\n"
        "• Quarantines suspicious messages for moderator review\n"
        "• Moderators can approve (✅) or reject (❌) flagged messages\n"
        "• Whitelists trusted domains (YouTube, Discord, GitHub, DeviantArt)\n\n"
        "**Setup:**\n"
        "1. Use `!reviewchannel <channel_id>` to set your mod review channel\n"
        "2. Ensure the bot has `Manage Messages` permission\n"
        "3. SentriBot will automatically monitor all messages!\n\n"
        "Need help? Contact your server administrator."
    )
    await ctx.send(help_text)

@bot.command(name="reviewchannel")
@commands.has_permissions(administrator=True)
async def reviewchannel_command(ctx, channel_id: int):
    """Set the moderation review channel (Admin only)"""
    global MOD_REVIEW_CHANNEL_ID
    
    # Verify the channel exists
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Could not find a channel with that ID.")
        return
    
    MOD_REVIEW_CHANNEL_ID = channel_id
    await ctx.send(f"✅ Review channel set to <#{channel_id}>")

@reviewchannel_command.error
async def reviewchannel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Only administrators can set the review channel.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!reviewchannel <channel_id>`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid channel ID. Please provide a numeric ID.")

# -------------------------------
# ON MESSAGE EVENT
# -------------------------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process commands first
    await bot.process_commands(message)

    # Whitelist: domains
    domains = extract_domains(message.content)
    for d in domains:
        if any(allowed in d for allowed in ALLOWED_DOMAINS):
            # Contains only safe domains → skip model
            return

    # Run the model
    is_spam, confidence = predict(message.content)

    if not is_spam:
        return
    
    # ---------------------------
    # QUARANTINE MESSAGE
    # ---------------------------
    try:
        await message.delete()
    except:
        pass

    # Notify the user their message is pending review
    try:
        await message.channel.send(
            f"{message.author.mention}, your message is pending review for potential spam. "
            f"Please refrain from sending malicious links or messages."
        )
    except:
        pass

    # Send to mod review channel
    if MOD_REVIEW_CHANNEL_ID is None:
        print("[SentriBot] No review channel set. Use !reviewchannel <channel_id> to set one.")
        return
    
    mod_channel = bot.get_channel(MOD_REVIEW_CHANNEL_ID)
    if not mod_channel:
        print(f"[SentriBot] Could not find review channel with ID {MOD_REVIEW_CHANNEL_ID}")
        return

    review_msg = await mod_channel.send(
        f"⚠️ **Potential Scam Detected**\n"
        f"**User:** {message.author.mention}\n"
        f"**Channel:** <#{message.channel.id}>\n"
        f"**Confidence:** {confidence:.2%}\n\n"
        f"**Content:**\n```{message.content}```\n"
        f"React with ✅ to approve and restore message.\n"
        f"React with ❌ to confirm deletion."
    )

    await review_msg.add_reaction("✅")
    await review_msg.add_reaction("❌")

    # Store original message metadata in dictionary
    pending_reviews[review_msg.id] = {
        "author": message.author,
        "content": message.content,
        "channel_id": message.channel.id,
    }

# -------------------------------
# Reaction Handler (Moderators Only)
# -------------------------------

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message = reaction.message
    if message.channel.id != MOD_REVIEW_CHANNEL_ID:
        return

    if reaction.emoji not in ["✅", "❌"]:
        return

    # Extract stored original message info
    data = pending_reviews.get(message.id)
    if not data:
        return

    target_channel = bot.get_channel(data["channel_id"])

    if reaction.emoji == "✅":
        # Restore the message publicly
        await target_channel.send(
            f"📥 **Approved message from {data['author'].mention}:**\n"
            f"{data['content']}"
        )
        await message.channel.send(f"✅ Message approved by {user.mention}")

    elif reaction.emoji == "❌":
        await message.channel.send(f"❌ Message confirmed as spam by {user.mention}")

    # Remove stored data after use
    pending_reviews.pop(message.id, None)

# -------------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    # Send startup message to guilds
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                startup_msg = (
                    "🦸 **SentriBot Online!** Spam protection active.\n\n"
                )
                
                if MOD_REVIEW_CHANNEL_ID is None:
                    startup_msg += (
                        "⚠️ **Setup Required:** Use `!reviewchannel <channel_id>` to set up "
                        "a channel for moderator review.\n\n"
                    )
                
                startup_msg += "Type `!help` for commands and features."
                
                await channel.send(startup_msg)
                break
        break

bot.run(TOKEN)
