# uses python v3.12.1
import ghost_support_bot
import discord
from discord.ext import commands
from get_stripe_products import get_products


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load products from Stripe
PRODUCTS = get_products()

# Payment links
PAYPAL_LINK = "https://www.paypal.com/paypalme/VirexCheese"
CRYPTO_NOTE = "Ask a staff member for the wallet address before sending. Also let them know what crypto you wanna pay with :)"
MONITOR_ROLE_ID = 1397841791138533436  # Replace with your actual role ID for admins/mods
ORDERS_CATEGORY_ID = 1398842986502164490     # Replace with your target category ID for private channels
COMPLETED_ORDERS_CATEGORY_ID = 1398844816649097358  # Replace with your finished orders category ID
ALLOWED_CHANNEL_ID = 1397865012713754665 # allowed channel for all bot commands from users
discord_word_limit = 2000
user_tabs = {}  # Maps user ID to browser tab/page instance


@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

# main command
@bot.command()
async def buy(ctx):
    # delete user's message (cleanup)
    await ctx.message.delete()

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send(f"❌ You can only use this command in the <#{ALLOWED_CHANNEL_ID}> channel.")
        return

    # Check if the user already has an open order in the orders category
    for channel in ctx.guild.text_channels:
        if (
            channel.category_id == ORDERS_CATEGORY_ID and
            channel.name == f"order-{ctx.author.name.lower()}"
        ):
            await ctx.send(f"🛑 You already have an open order: {channel.mention}")
            return
    

    guild = ctx.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.get_role(MONITOR_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    channel_name = f"order-{ctx.author.name.lower()}"
    channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=discord.Object(id=ORDERS_CATEGORY_ID))

    view = ProductSelectView(ctx.author, channel)
    await channel.send(f"**Hi {ctx.author.mention}, select a product below to get started:**", view=view)

class ProductSelect(discord.ui.Select):
    def __init__(self, user, channel):
        self.user = user
        self.channel = channel
        options = [
            discord.SelectOption(label=label, description=f"Price: {info['price']}")
            for label, info in PRODUCTS.items()
        ]
        super().__init__(placeholder="Choose your product...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't use this menu.", ephemeral=True)
            return

        product = self.values[0]
        info = PRODUCTS[product]
        tag = str(interaction.user)

        note = f"{product} | Discord: {tag}"
        msg = (
            f"**🛒 Product:** {product}\n"
            f"**💰 Price:** {info['price']}\n"
            f"**📋 Copy this note when using PayPal:**\n```{note}```\n\n"
            f"**:white_check_mark: STRIPE**\n"
            f"> [Pay with Stripe]({info['link']})\n"
            f"**:white_check_mark: PAYPAL**\n"
            f"> [Pay with PayPal](<{PAYPAL_LINK}>)\n"
            f"**:white_check_mark: CRYPTO**\n"
            f"> {CRYPTO_NOTE}\n"
            f"**Need Another Option?**\n"  
            f"> DM a staff member or open a ticket."
        )
            # Edit the original message instead of sending new ones

        await interaction.response.edit_message(content=msg, view=self.view)
        # Keep the dropdown active for further selections
        if self.view is not None:
            self.view.clear_items()
            self.view.add_item(ProductSelect(self.user, self.channel))

        if interaction.message is not None:
            await interaction.message.edit(view=self.view)

class ProductSelectView(discord.ui.View):
    def __init__(self, user, channel):
        super().__init__(timeout=None)
        self.add_item(ProductSelect(user, channel))



@bot.command()
@commands.has_role(MONITOR_ROLE_ID)
async def completeorder(ctx):
    channel = ctx.channel
    guild = ctx.guild
    if channel.category_id != ORDERS_CATEGORY_ID:
        await ctx.send("This command can only be used in an active order channel.")
        return

    transcript = []
    async for message in channel.history(limit=None, oldest_first=True):
        author = message.author.display_name
        content = message.clean_content
        transcript.append(f"[{author}] {content}")

    transcript_text = "\n".join(transcript)

    # Create a new channel in the finished category
    finished_channel = await guild.create_text_channel(channel.name, category=discord.Object(id=COMPLETED_ORDERS_CATEGORY_ID))
    await finished_channel.set_permissions(guild.default_role, read_messages=False)
    await finished_channel.set_permissions(guild.get_role(MONITOR_ROLE_ID), read_messages=True, send_messages=False)

    # Send the transcript
    for chunk in [transcript_text[i:i+1900] for i in range(0, len(transcript_text), 1900)]:
        await finished_channel.send(f"```{chunk}```")

    await ctx.send("✅ Order finished and logged.")
    await channel.delete()

@bot.command()
async def helpme(ctx):
    await ctx.message.delete()

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send(f"❌ You can only use this command in the <#{ALLOWED_CHANNEL_ID}> channel.")
        return

    guild = ctx.guild
    channel_name = f"inquiry-{ctx.author.name.lower()}"

    # Check if an inquiry already exists
    for channel in guild.text_channels:
        if channel.name == channel_name and channel.category_id == ORDERS_CATEGORY_ID:
            await ctx.send(f"🛑 You already have an open inquiry: {channel.mention}")
            return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.get_role(MONITOR_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }


    inquiry_channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=discord.Object(id=ORDERS_CATEGORY_ID))

    await ghost_support_bot.open_tab_for_user(ctx.author.id)


    # Send the placeholder instruction message
    await inquiry_channel.send(
        f"👋 Hello {ctx.author.mention}, welcome to your private inquiry channel!\n\n"
        f"To chat with Ghost, simply type:\n```!chat your message here```\n\n"
        f"When you're done, a staff member will close this session."
    )




@bot.command()
async def chat(ctx, *, message = ""):

    if not ctx.channel.name.startswith("inquiry-") or ctx.channel.category_id != ORDERS_CATEGORY_ID:
        await ctx.send("❌ This command can only be used inside your private Ghost inquiry channel.")
        return

    if message.strip() == "" or len(message.strip()) == 0:
        await ctx.reply("🛑 Please provide a message to send.")
        return

    await ghost_support_bot.send_prompt(ctx.author.id, message)

    thinking_msg = await ctx.reply("Ghost is responding...")

    response = await ghost_support_bot.get_latest_response(ctx.author.id)

    if response.strip():
        await thinking_msg.edit(content=response[:discord_word_limit])
    else:
        await thinking_msg.edit(content="[!] No response generated or failed to extract.")


@bot.command()
@commands.has_role(MONITOR_ROLE_ID)
async def endchatsession(ctx):
    channel = ctx.channel
    guild = ctx.guild

    if not channel.name.startswith("inquiry-") or channel.category_id != ORDERS_CATEGORY_ID:
        await ctx.send("This command can only be used in an active inquiry channel.")
        return

    transcript = []
    async for message in channel.history(limit=None, oldest_first=True):
        author = message.author.display_name
        content = message.clean_content
        transcript.append(f"[{author}] {content}")

    transcript_text = "\n".join(transcript)

    # Create a new channel in the finished category
    finished_channel = await guild.create_text_channel(channel.name, category=discord.Object(id=COMPLETED_ORDERS_CATEGORY_ID))
    await finished_channel.set_permissions(guild.default_role, read_messages=False)
    await finished_channel.set_permissions(guild.get_role(MONITOR_ROLE_ID), read_messages=True, send_messages=False)

    for chunk in [transcript_text[i:i+1900] for i in range(0, len(transcript_text), 1900)]:
        await finished_channel.send(f"```{chunk}```")

    await ctx.send("✅ Inquiry closed and logged.")

    await ghost_support_bot.close_tab_for_user(ctx.author.id)

    await channel.delete()


def run():
    ghost_support_bot.start()
    from get_tokens import discord_bot_token
    bot.run(discord_bot_token)