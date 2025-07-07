import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
from discord import app_commands
import glob

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)  # Changed from None to "!"

# Data storage (in production, use a proper database)
focus_sessions = {}
exam_dates = {}
resources = {}  # Store resources by subject

# File paths for persistent data
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
RESOURCES_FILE = os.path.join(DATA_DIR, 'resources.json')
EXAM_DATES_FILE = os.path.join(DATA_DIR, 'exam_dates.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Load persistent data
def load_persistent_data():
    """Load resources and exam dates from JSON files"""
    global resources, exam_dates
    
    # Load resources
    try:
        if os.path.exists(RESOURCES_FILE):
            with open(RESOURCES_FILE, 'r') as f:
                resources = json.load(f)
                print(f"Loaded {sum(len(resources[subject]) for subject in resources)} resources")
    except Exception as e:
        print(f"Error loading resources: {e}")
        resources = {}
    
    # Load exam dates
    try:
        if os.path.exists(EXAM_DATES_FILE):
            with open(EXAM_DATES_FILE, 'r') as f:
                exam_data = json.load(f)
                # Convert datetime strings back to datetime objects
                exam_dates = {}
                for exam_name, data in exam_data.items():
                    exam_dates[exam_name] = {
                        'name': data['name'],
                        'datetime': datetime.fromisoformat(data['datetime']),
                        'set_by': data['set_by']
                    }
                print(f"Loaded {len(exam_dates)} exam dates")
    except Exception as e:
        print(f"Error loading exam dates: {e}")
        exam_dates = {}

def save_resources():
    """Save resources to JSON file"""
    try:
        with open(RESOURCES_FILE, 'w') as f:
            json.dump(resources, f, indent=2)
    except Exception as e:
        print(f"Error saving resources: {e}")

def save_exam_dates():
    """Save exam dates to JSON file"""
    try:
        # Convert datetime objects to strings for JSON serialization
        exam_data = {}
        for exam_name, data in exam_dates.items():
            exam_data[exam_name] = {
                'name': data['name'],
                'datetime': data['datetime'].isoformat(),
                'set_by': data['set_by']
            }
        with open(EXAM_DATES_FILE, 'w') as f:
            json.dump(exam_data, f, indent=2)
    except Exception as e:
        print(f"Error saving exam dates: {e}")

# Load data on startup
load_persistent_data()

# --- Load subject conversion tables from JSON files ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Map subject command names to JSON filenames
SUBJECT_JSON_MAP = {
    "english_hl": "eng.json",
    "french_sl": "fsf.json",
    "french_hl": "fif.json",
    "spanish_sl": "esp.json",
    "economics_hl": "econ.json",
    "geography_hl": "geo.json",
    "business_sl": "bbb.json",
    "chemistry_sl": "scha.json",
    "chemistry_hl": "schb.json",
    "biology_sl": "sbia.json",
    "biology_hl": "sbib.json",
    "physics_sl": "sph.json",
    "math_sl": "mtha.json",
    "math_hl": "mthb.json"
}

SUBJECT_CONVERSIONS = {}
for subject, filename in SUBJECT_JSON_MAP.items():
    try:
        with open(os.path.join(DATA_DIR, filename), 'r') as f:
            SUBJECT_CONVERSIONS[subject] = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filename} for {subject}: {e}")

# --- Conversion functions using new structure ---
def raw_to_converted(raw_mark, subject="physics_sl"):
    """Convert raw IB mark to converted Ontario mark using loaded JSON tables"""
    if subject not in SUBJECT_CONVERSIONS:
        subject = "physics_sl"
    data = SUBJECT_CONVERSIONS[subject]
    # Flatten all levels into one dict
    flat = {int(k): v for level in data.values() for k, v in level.items()}
    raw_mark = int(raw_mark)
    if str(raw_mark) in [k for level in data.values() for k in level.keys()]:
        # Find the value directly
        for level in data.values():
            if str(raw_mark) in level:
                return level[str(raw_mark)]
    # Interpolate if not found
    keys = sorted(flat.keys())
    if raw_mark <= keys[0]:
        return flat[keys[0]]
    if raw_mark >= keys[-1]:
        return flat[keys[-1]]
    for i in range(len(keys)-1):
        if keys[i] <= raw_mark <= keys[i+1]:
            x1, x2 = keys[i], keys[i+1]
            y1, y2 = flat[x1], flat[x2]
            return round(y1 + (y2-y1)*(raw_mark-x1)/(x2-x1))
    return flat[keys[0]]

def raw_to_ib_level(raw_mark, subject="physics_sl"):
    """Convert raw IB mark to IB level (1-7) using loaded JSON tables"""
    if subject not in SUBJECT_CONVERSIONS:
        subject = "physics_sl"
    data = SUBJECT_CONVERSIONS[subject]
    for level in range(7, 0, -1):
        level_key = f"Level {level}"
        if level_key in data and str(raw_mark) in data[level_key]:
            return level
    # If not found, try to infer by converted mark
    converted = raw_to_converted(raw_mark, subject)
    return percentage_to_ib_level(converted, subject)

def percentage_to_ib_level(percentage, subject="physics_sl"):
    """Convert Ontario percentage to IB level using loaded JSON tables"""
    if subject not in SUBJECT_CONVERSIONS:
        subject = "physics_sl"
    data = SUBJECT_CONVERSIONS[subject]
    # Find the highest level where any value in that level is <= percentage
    for level in range(7, 0, -1):
        level_key = f"Level {level}"
        if level_key in data:
            for v in data[level_key].values():
                if percentage >= v:
                    return level
    return 1

def ib_level_to_percentage(ib_level, subject="physics_sl"):
    """Convert IB level (1-7) to minimum Ontario percentage using loaded JSON tables"""
    if subject not in SUBJECT_CONVERSIONS:
        subject = "physics_sl"
    data = SUBJECT_CONVERSIONS[subject]
    level_key = f"Level {ib_level}"
    if level_key in data:
        # Return the minimum percentage for this level
        return min([int(v) for v in data[level_key].values()])
    return 0

# IB Level boundaries (converted marks) - Subject-specific
# Based on actual WOSS IB boundaries
IB_LEVEL_BOUNDARIES = {
    "math_sl": {
        1: 0,    # <50%
        2: 50,   # 50-60%
        3: 61,   # 61-71%
        4: 72,   # 72-83%
        5: 84,   # 84-92%
        6: 93,   # 93-96%
        7: 97    # 97-100%
    },
    "math_hl": {
        1: 0,    # <50%
        2: 50,   # 50-60%
        3: 61,   # 61-71%
        4: 72,   # 72-83%
        5: 84,   # 84-92%
        6: 93,   # 93-96%
        7: 97    # 97-100%
    },
    # Default boundaries for other subjects (can be updated as we get more data)
    "default": {
        1: 0,    # 0% = Level 1
        2: 50,   # 50% = Level 2
        3: 61,   # 61% = Level 3
        4: 72,   # 72% = Level 4
        5: 84,   # 84% = Level 5
        6: 93,   # 93% = Level 6
        7: 97    # 97% = Level 7
    }
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} guilds')
    
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')
    
    try:
        # Sync commands globally
        synced_global = await bot.tree.sync()
        print(f"Synced {len(synced_global)} global command(s)")
        
        # List all commands that were synced
        for command in synced_global:
            print(f"  Command: /{command.name} - {command.description}")
            
    except discord.Forbidden:
        print("❌ Bot doesn't have permission to sync commands!")
        print("Make sure the bot was invited with 'applications.commands' scope")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
        print(f"Error type: {type(e).__name__}")
    
    # Start the focus session checker
    check_focus_sessions.start()
    # Start exam countdown updater
    update_exam_countdowns.start()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors in slash commands"""
    if isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        if isinstance(original_error, discord.NotFound):
            # Interaction timed out
            try:
                await interaction.followup.send("⏰ The interaction timed out. Please try the command again.", ephemeral=True)
            except:
                pass
        else:
            # Other errors
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(original_error)}", ephemeral=True)
            except:
                pass
    else:
        # App command errors
        try:
            await interaction.followup.send(f"❌ Command error: {str(error)}", ephemeral=True)
        except:
            pass

@bot.event
async def on_message(message):
    """Handle regular messages - ignore them since we use slash commands"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Don't process commands for regular messages since we use slash commands
    # This prevents the prefix errors
    pass

# Focus Mode Commands
@bot.tree.command(name="focus", description="Start a focus session (duration in minutes)")
@app_commands.describe(
    duration="Duration in minutes (max 480)",
    mode="Choose focus mode type"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="Deep Focus", value="deep"),
    app_commands.Choice(name="Study Group", value="study_group"),
    app_commands.Choice(name="Physics", value="physics"),
    app_commands.Choice(name="Chemistry", value="chemistry"),
    app_commands.Choice(name="Biology", value="biology"),
    app_commands.Choice(name="Math", value="math"),
    app_commands.Choice(name="English", value="english"),
    app_commands.Choice(name="French", value="french"),
    app_commands.Choice(name="Spanish", value="spanish"),
    app_commands.Choice(name="Geography", value="geography"),
    app_commands.Choice(name="History", value="history"),
    app_commands.Choice(name="Economics", value="economics"),
    app_commands.Choice(name="Business", value="business"),
])
async def focus_start(interaction: discord.Interaction, duration: int, mode: str = "deep"):
    """
    Start a focus session
    duration: Duration in minutes
    mode: Focus mode type (deep, study_group, subject)
    """
    user_id = interaction.user.id
    guild = interaction.guild
    
    if user_id in focus_sessions:
        await interaction.response.send_message("❌ You're already in a focus session! Use `/unfocus` to end it first.", ephemeral=True)
        return
    
    if duration > 480:  # 8 hours max
        await interaction.response.send_message("❌ Focus sessions cannot exceed 8 hours (480 minutes).", ephemeral=True)
        return
    
    # Create or get focus role
    focus_role_name = f"🔒 Locked In ({mode.title()})"
    focus_role = discord.utils.get(guild.roles, name=focus_role_name)
    # If the role does not exist, do not create it (commented out)
    # if not focus_role:
    #     try:
    #         focus_role = await guild.create_role(
    #             name=focus_role_name,
    #             color=discord.Color.red(),
    #             reason="Focus mode role creation"
    #         )
    #     except discord.Forbidden:
    #         await interaction.response.send_message("❌ I don't have permission to create roles.", ephemeral=True)
    #         return
    if not focus_role:
        await interaction.response.send_message("❌ The 'Locked In' role does not exist. Please ask an admin to create it.", ephemeral=True)
        return
    
    # Add role to user
    try:
        await interaction.user.add_roles(focus_role, reason=f"Focus session started for {duration} minutes")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to assign roles.", ephemeral=True)
        return
    
    # Store focus session data
    end_time = datetime.now() + timedelta(minutes=duration)
    focus_sessions[user_id] = {
        'end_time': end_time,
        'role': focus_role,
        'mode': mode,
        'duration': duration,
        'user': interaction.user
    }
    
    embed = discord.Embed(
        title="🔒 Locked In Activated!",
        description=f"**Mode:** {mode.title()}\n**Duration:** {duration} minutes\n**Ends at:** <t:{int(end_time.timestamp())}:t>",
        color=discord.Color.red()
    )
    embed.add_field(
        name="What's restricted:",
        value="• Casual chat channels\n• Meme channels\n• Gaming channels\n• Off-topic discussions",
        inline=False
    )
    embed.set_footer(text="Stay locked in! You got this! 📚")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unfocus", description="Request to end your current focus session (admin approval required)")
async def unfocus(interaction: discord.Interaction):
    """Request to end the current focus session (admin approval required)"""
    user_id = interaction.user.id
    guild = interaction.guild
    admin_role = discord.utils.get(guild.roles, name="Admins")
    if user_id not in focus_sessions:
        await interaction.response.send_message("❌ You're not currently in a focus session.", ephemeral=False)
        return

    session_data = focus_sessions[user_id]
    user = interaction.user

    class ConfirmUnfocusView(discord.ui.View):
        def __init__(self, target_user, timeout=120):
            super().__init__(timeout=timeout)
            self.target_user = target_user

        async def interaction_check(self, button_interaction: discord.Interaction) -> bool:
            # Only allow admins to press the buttons
            admin_role = discord.utils.get(button_interaction.guild.roles, name="Admins")
            if admin_role and admin_role in button_interaction.user.roles:
                return True
            await button_interaction.response.send_message("❌ Only admins can approve or refuse this request.", ephemeral=True)
            return False

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            session_data = focus_sessions.get(self.target_user.id)
            if session_data:
                try:
                    await self.target_user.remove_roles(session_data['role'], reason="Focus session ended by admin approval")
                except discord.Forbidden:
                    pass
                started_time = session_data['end_time'] - timedelta(minutes=session_data['duration'])
                actual_duration = datetime.now() - started_time
                actual_minutes = int(actual_duration.total_seconds() / 60)
                del focus_sessions[self.target_user.id]
                embed = discord.Embed(
                    title="✅ Focus Session Ended (Admin Confirmed)",
                    description=f"{self.target_user.mention}'s focus session has been ended by {button_interaction.user.mention} (admin).\nGreat work! You focused for **{actual_minutes} minutes**.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Session Stats:",
                    value=f"**Planned:** {session_data['duration']} minutes\n**Actual:** {actual_minutes} minutes\n**Mode:** {session_data['mode'].title()}",
                    inline=False
                )
                embed.set_footer(text="Keep up the great work! 🌟")
                await button_interaction.response.edit_message(embed=embed, view=None)
            else:
                await button_interaction.response.edit_message(content="❌ No active focus session found.", view=None)
            self.stop()

        @discord.ui.button(label="Refuse", style=discord.ButtonStyle.red)
        async def refuse(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="❌ Unfocus Request Refused",
                description=f"{self.target_user.mention}'s request to end their focus session was refused by {button_interaction.user.mention} (admin).",
                color=discord.Color.red()
            )
            await button_interaction.response.edit_message(embed=embed, view=None)
            self.stop()

    embed = discord.Embed(
        title="⚠️ Unfocus Request Pending",
        description=f"{user.mention} has requested to end their focus session.\n\n**An admin must approve or refuse this request below.**",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="Session Info:",
        value=f"**Mode:** {session_data['mode'].title()}\n**Planned Duration:** {session_data['duration']} minutes\n**Ends at:** <t:{int(session_data['end_time'].timestamp())}:t>",
        inline=False
    )
    embed.set_footer(text="Only admins can approve or refuse this request.")
    view = ConfirmUnfocusView(user)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="focus_status", description="Check your current focus session status")
async def focus_status(interaction: discord.Interaction):
    """Check focus session status"""
    user_id = interaction.user.id
    
    if user_id not in focus_sessions:
        await interaction.response.send_message("❌ You're not currently in a focus session.", ephemeral=True)
        return
    
    session_data = focus_sessions[user_id]
    end_time = session_data['end_time']
    time_remaining = end_time - datetime.now()
    
    if time_remaining.total_seconds() <= 0:
        await interaction.response.send_message("⏰ Your focus session has ended! Use `/unfocus` to complete it.", ephemeral=True)
        return
    
    minutes_remaining = int(time_remaining.total_seconds() / 60)
    
    embed = discord.Embed(
        title="🎯 Focus Session Status",
        description=f"**Time Remaining:** {minutes_remaining} minutes\n**Ends at:** <t:{int(end_time.timestamp())}:t>\n**Mode:** {session_data['mode'].title()}",
        color=discord.Color.red()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="focus_list", description="Show all users currently Locked In")
async def focus_list(interaction: discord.Interaction):
    """Show all users currently Locked In"""
    if not focus_sessions:
        embed = discord.Embed(
            title="🔒 Locked In Status",
            description="No users are currently Locked In.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="🔒 Users Locked In",
        color=discord.Color.orange()
    )
    
    current_time = datetime.now()
    active_sessions = []
    
    for user_id, session_data in focus_sessions.items():
        time_remaining = session_data['end_time'] - current_time
        
        if time_remaining.total_seconds() > 0:
            minutes_remaining = int(time_remaining.total_seconds() / 60)
            user = session_data['user']
            mode = session_data['mode'].title()
            
            active_sessions.append({
                'user': user,
                'minutes_remaining': minutes_remaining,
                'mode': mode,
                'end_time': session_data['end_time']
            })
    
    if not active_sessions:
        embed.description = "No active focus sessions found."
    else:
        # Sort by time remaining (shortest first)
        active_sessions.sort(key=lambda x: x['minutes_remaining'])
        
        for session in active_sessions:
            user = session['user']
            minutes = session['minutes_remaining']
            mode = session['mode']
            end_time = session['end_time']
            
            embed.add_field(
                name=f"👤 {user.display_name}",
                value=f"**Mode:** {mode}\n**Time Left:** {minutes} minutes\n**Ends:** <t:{int(end_time.timestamp())}:t>",
                inline=True
            )
    
    embed.set_footer(text=f"Total active sessions: {len(active_sessions)}")
    
    await interaction.response.send_message(embed=embed)

# IB Score Conversion Commands
@bot.tree.command(name="raw_to_converted", description="Convert raw IB mark to Ontario percentage")
@app_commands.describe(
    raw_mark="Your raw IB test mark (0-100)",
    subject="Choose the subject"
)
@app_commands.choices(subject=[
    app_commands.Choice(name="HL English", value="english_hl"),
    app_commands.Choice(name="SL French", value="french_sl"),
    app_commands.Choice(name="HL French", value="french_hl"),
    app_commands.Choice(name="SL Spanish", value="spanish_sl"),
    app_commands.Choice(name="HL Economics", value="economics_hl"),
    app_commands.Choice(name="HL Geography", value="geography_hl"),
    app_commands.Choice(name="SL Business", value="business_sl"),
    app_commands.Choice(name="SL Chemistry", value="chemistry_sl"),
    app_commands.Choice(name="HL Chemistry", value="chemistry_hl"),
    app_commands.Choice(name="SL Biology", value="biology_sl"),
    app_commands.Choice(name="HL Biology", value="biology_hl"),
    app_commands.Choice(name="SL Physics", value="physics_sl"),
    app_commands.Choice(name="SL Math", value="math_sl"),
    app_commands.Choice(name="HL Math", value="math_hl"),
])
async def raw_to_converted_cmd(interaction: discord.Interaction, raw_mark: int, subject: str):
    """Convert raw IB mark to Ontario percentage"""
    if raw_mark not in range(0, 101):
        try:
            await interaction.response.send_message("❌ Raw mark must be between 0 and 100.", ephemeral=True)
        except discord.NotFound:
            # Interaction timed out, try to send a followup
            try:
                await interaction.followup.send("❌ Raw mark must be between 0 and 100.", ephemeral=True)
            except:
                pass
        return
    
    converted = raw_to_converted(raw_mark, subject)
    ib_level = raw_to_ib_level(raw_mark, subject)
    
    embed = discord.Embed(
        title="📊 Raw to Converted Mark",
        description=f"**Subject:** {subject.replace('_', ' ').title()}\n**Raw Mark:** {raw_mark}%",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Results:",
        value=f"**Ontario Mark:** {converted}%\n**IB Level:** {ib_level}",
        inline=False
    )
    
    try:
        await interaction.response.send_message(embed=embed)
    except discord.NotFound:
        # Interaction timed out, try to send a followup
        try:
            await interaction.followup.send(embed=embed)
        except:
            # If all else fails, try to send a DM
            try:
                await interaction.user.send(embed=embed)
            except:
                pass

@bot.tree.command(name="ib_to_percent", description="Convert IB grade to percentage")
@app_commands.describe(
    ib_grade="IB grade (1-7)",
    subject="Choose the subject (optional)"
)
@app_commands.choices(subject=[
    app_commands.Choice(name="General (Default)", value="default"),
    app_commands.Choice(name="Math SL", value="math_sl"),
    app_commands.Choice(name="Math HL", value="math_hl"),
    app_commands.Choice(name="Physics SL", value="physics_sl"),
    app_commands.Choice(name="Physics HL", value="physics_hl"),
    app_commands.Choice(name="Chemistry SL", value="chemistry_sl"),
    app_commands.Choice(name="Chemistry HL", value="chemistry_hl"),
    app_commands.Choice(name="Biology SL", value="biology_sl"),
    app_commands.Choice(name="Biology HL", value="biology_hl"),
    app_commands.Choice(name="English SL", value="english_sl"),
    app_commands.Choice(name="English HL", value="english_hl"),
    app_commands.Choice(name="French SL", value="french_sl"),
    app_commands.Choice(name="French HL", value="fif.json"),
    app_commands.Choice(name="Spanish SL", value="esp.json"),
    app_commands.Choice(name="Geography SL", value="geo.json"),
    app_commands.Choice(name="Geography HL", value="geo.json"),
    app_commands.Choice(name="History SL", value="bbb.json"),
    app_commands.Choice(name="History HL", value="bbb.json"),
    app_commands.Choice(name="Economics SL", value="econ.json"),
    app_commands.Choice(name="Economics HL", value="econ.json"),
])
async def ib_to_percent(interaction: discord.Interaction, ib_grade: int, subject: str = "default"):
    """Convert IB grade (1-7) to percentage using JSON data if available"""
    if ib_grade not in range(1, 8):
        await interaction.response.send_message("❌ IB grades must be between 1 and 7.", ephemeral=True)
        return
    
    # Use JSON data if available
    if subject in SUBJECT_CONVERSIONS:
        data = SUBJECT_CONVERSIONS[subject]
        level_key = f"Level {ib_grade}"
        if level_key in data:
            # Get all percentages for this level and use the minimum
            percentages = [int(v) for v in data[level_key].values()]
            if percentages:
                percentage = min(percentages)
                # Find the next level's minimum for the range
                if ib_grade < 7:
                    next_level_key = f"Level {ib_grade+1}"
                    if next_level_key in data:
                        next_percentages = [int(v) for v in data[next_level_key].values()]
                        if next_percentages:
                            next_level_min = min(next_percentages)
                        else:
                            next_level_min = 100
                    else:
                        next_level_min = 100
                    range_text = f"**{percentage}% - {next_level_min-1}%**"
                else:
                    range_text = f"**{percentage}% - 100%**"
                subject_name = subject.replace('_', ' ').title()
    embed = discord.Embed(
        title="📊 IB Grade Conversion",
        description=f"**IB Grade {ib_grade}** = **{percentage}%** (minimum)\n**Subject:** {subject_name}",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Level Range:",
        value=range_text,
        inline=False
        )
    embed.add_field(
        name="Note:",
        value="This shows the minimum converted percentage required for each IB level. Actual raw marks vary by subject.",
        inline=False
    )
    await interaction.response.send_message(embed=embed)
    return
    # Fallback to default boundaries
    if subject in IB_LEVEL_BOUNDARIES:
        boundaries = IB_LEVEL_BOUNDARIES[subject]
        subject_name = subject.replace('_', ' ').title()
    else:
        boundaries = IB_LEVEL_BOUNDARIES["default"]
        subject_name = "General"
    percentage = boundaries[ib_grade]
    if ib_grade < 7:
        next_level_min = boundaries[ib_grade + 1]
        range_text = f"**{percentage}% - {next_level_min - 1}%**"
    else:
        range_text = f"**{percentage}% - 100%**"
    embed = discord.Embed(
        title="📊 IB Grade Conversion",
        description=f"**IB Grade {ib_grade}** = **{percentage}%** (minimum)\n**Subject:** {subject_name}",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Level Range:",
        value=range_text,
        inline=False
    )
    embed.add_field(
        name="Note:",
        value="This shows the minimum converted percentage required for each IB level. Actual raw marks vary by subject.",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="subject_conversion", description="Show conversion table for a specific subject")
@app_commands.describe(subject="Choose the subject")
@app_commands.choices(subject=[
    app_commands.Choice(name="Physics SL", value="physics_sl"),
    app_commands.Choice(name="Physics HL", value="physics_hl"),
    app_commands.Choice(name="Chemistry SL", value="chemistry_sl"),
    app_commands.Choice(name="Chemistry HL", value="chemistry_hl"),
    app_commands.Choice(name="Biology SL", value="biology_sl"),
    app_commands.Choice(name="Biology HL", value="biology_hl"),
    app_commands.Choice(name="Math SL", value="math_sl"),
    app_commands.Choice(name="Math HL", value="math_hl"),
    app_commands.Choice(name="English SL", value="english_sl"),
    app_commands.Choice(name="English HL", value="english_hl"),
    app_commands.Choice(name="French SL", value="french_sl"),
    app_commands.Choice(name="French HL", value="french_hl"),
    app_commands.Choice(name="Spanish SL", value="spanish_sl"),
    app_commands.Choice(name="Geography SL", value="geography_sl"),
    app_commands.Choice(name="Geography HL", value="geography_hl"),
    app_commands.Choice(name="History SL", value="history_sl"),
    app_commands.Choice(name="History HL", value="history_hl"),
    app_commands.Choice(name="Economics SL", value="economics_sl"),
    app_commands.Choice(name="Economics HL", value="economics_hl"),
    app_commands.Choice(name="Business Management SL", value="business_sl"),
])
async def subject_conversion(interaction: discord.Interaction, subject: str):
    """Show the conversion table for a specific subject"""
    # Get the appropriate boundaries for the subject
    if subject in IB_LEVEL_BOUNDARIES:
        boundaries = IB_LEVEL_BOUNDARIES[subject]
    else:
        boundaries = IB_LEVEL_BOUNDARIES["default"]
    
    embed = discord.Embed(
        title=f"📊 {subject.replace('_', ' ').title()} IB Level Boundaries",
        description="IB levels → Ontario percentages (minimum required)",
        color=discord.Color.green()
    )
    
    # Create a formatted table showing IB level boundaries
    table_rows = []
    for level in range(1, 8):
        min_percent = boundaries[level]
        if level < 7:
            max_percent = boundaries[level + 1] - 1
            table_rows.append(f"**Level {level}:** {min_percent}% - {max_percent}%")
        else:
            table_rows.append(f"**Level {level}:** {min_percent}% - 100%")
    
    embed.add_field(
        name="Level Boundaries:",
        value="\n".join(table_rows),
        inline=False
    )
    
    embed.set_footer(text="Based on WOSS IB conversion tables")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_subjects", description="List all available subjects for conversion")
async def list_subjects(interaction: discord.Interaction):
    """List all available subjects for grade conversion"""
    embed = discord.Embed(
        title="📚 Available Subjects",
        description="Use these subject names with conversion commands:",
        color=discord.Color.purple()
    )
    
    # Group subjects by type
    sciences = [s for s in SUBJECT_CONVERSIONS.keys() if any(subj in s for subj in ['physics', 'chemistry', 'biology'])]
    languages = [s for s in SUBJECT_CONVERSIONS.keys() if any(subj in s for subj in ['english', 'french', 'spanish'])]
    humanities = [s for s in SUBJECT_CONVERSIONS.keys() if any(subj in s for subj in ['geography', 'history', 'economics'])]
    business = [s for s in SUBJECT_CONVERSIONS.keys() if any(subj in s for subj in ['business'])]
    math = [s for s in SUBJECT_CONVERSIONS.keys() if 'math' in s]
    
    embed.add_field(
        name="🔬 Sciences",
        value="\n".join([f"• `{s}`" for s in sorted(sciences)]),
        inline=True
    )
    embed.add_field(
        name="📖 Languages",
        value="\n".join([f"• `{s}`" for s in sorted(languages)]),
        inline=True
    )
    embed.add_field(
        name="🌍 Humanities",
        value="\n".join([f"• `{s}`" for s in sorted(humanities)]),
        inline=True
    )
    embed.add_field(
        name="📊 Business",
        value="\n".join([f"• `{s}`" for s in sorted(business)]),
        inline=True
    )
    embed.add_field(
        name="📐 Mathematics",
        value="\n".join([f"• `{s}`" for s in sorted(math)]),
        inline=True
    )
    
    embed.set_footer(text="Use /raw_to_converted <mark> <subject> to convert your marks")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="calculate_total", description="Calculate total IB score from individual grades")
@app_commands.describe(
    subject1="IB grade for subject 1 (1-7)",
    subject2="IB grade for subject 2 (1-7)",
    subject3="IB grade for subject 3 (1-7)",
    subject4="IB grade for subject 4 (1-7)",
    subject5="IB grade for subject 5 (1-7)",
    subject6="IB grade for subject 6 (1-7)",
    tok_ee_bonus="TOK/EE bonus points (0-3, optional)"
)
async def calculate_total(interaction: discord.Interaction, 
                         subject1: int, subject2: int, subject3: int, 
                         subject4: int, subject5: int, subject6: int,
                         tok_ee_bonus: int = 0):
    """Calculate total IB diploma score"""
    subjects = [subject1, subject2, subject3, subject4, subject5, subject6]
    
    # Validate grades
    for i, grade in enumerate(subjects, 1):
        if grade not in range(1, 8):
            await interaction.response.send_message(f"❌ Subject {i} grade must be between 1 and 7.", ephemeral=True)
            return
    
    if tok_ee_bonus not in range(0, 4):
        await interaction.response.send_message("❌ TOK/EE bonus points must be between 0 and 3.", ephemeral=True)
        return
    
    total_score = sum(subjects) + tok_ee_bonus
    subject_total = sum(subjects)
    
    # Determine diploma status
    if total_score >= 24 and all(grade >= 3 for grade in subjects) and subject_total >= 12:
        diploma_status = "✅ **DIPLOMA AWARDED**"
        status_color = discord.Color.green()
    else:
        diploma_status = "❌ **DIPLOMA NOT AWARDED**"
        status_color = discord.Color.red()
    
    embed = discord.Embed(
        title="🎓 IB Diploma Score Calculator",
        description=diploma_status,
        color=status_color
    )
    
    subjects_text = " + ".join([str(grade) for grade in subjects])
    embed.add_field(
        name="Score Breakdown:",
        value=f"**Subjects:** {subjects_text} = {subject_total}\n**TOK/EE Bonus:** {tok_ee_bonus}\n**Total Score:** {total_score}/45",
        inline=False
    )
    
    # Add grade distribution
    grade_counts = {}
    for grade in subjects:
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    
    distribution = ", ".join([f"{count}×{grade}" for grade, count in sorted(grade_counts.items(), reverse=True)])
    embed.add_field(name="Grade Distribution:", value=distribution, inline=False)
    
    # Add conversion note
    embed.add_field(
        name="💡 Note:",
        value="Use `/raw_to_converted` to convert your actual test marks to IB levels!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Exam Countdown Commands
@bot.tree.command(name="set_exam", description="Set an exam date for countdown")
@app_commands.describe(
    exam_name="Name of the exam (e.g., Physics SL Paper 1)",
    date="Exam date in YYYY-MM-DD format",
    time="Exam time in HH:MM format (24-hour, optional)"
)
async def set_exam(interaction: discord.Interaction, exam_name: str, date: str, time: str = "09:00"):
    """
    Set exam date for countdown
    Format: date as YYYY-MM-DD, time as HH:MM (24-hour format)
    """
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You need 'Manage Channels' permission to set exam dates.", ephemeral=True)
        return
    
    try:
        exam_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        await interaction.response.send_message("❌ Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for time.", ephemeral=True)
        return
    
    if exam_datetime <= datetime.now():
        await interaction.response.send_message("❌ Exam date must be in the future.", ephemeral=True)
        return
    
    exam_dates[exam_name.lower()] = {
        'name': exam_name,
        'datetime': exam_datetime,
        'set_by': interaction.user.id
    }
    
    # Save exam dates to file
    save_exam_dates()
    
    embed = discord.Embed(
        title="📅 Exam Date Set!",
        description=f"**{exam_name}**\n<t:{int(exam_datetime.timestamp())}:F>",
        color=discord.Color.orange()
    )
    
    time_until = exam_datetime - datetime.now()
    days_until = time_until.days
    
    embed.add_field(
        name="Time Until Exam:",
        value=f"**{days_until} days** ({time_until.total_seconds() / 3600:.1f} hours)",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="exam_countdown", description="Show countdown to specific exam")
@app_commands.describe(exam_name="Name of the exam (leave empty to show all)")
async def exam_countdown(interaction: discord.Interaction, exam_name: str = None):
    """Show countdown to exam(s)"""
    if not exam_dates:
        await interaction.response.send_message("❌ No exam dates have been set yet.", ephemeral=True)
        return
    
    if exam_name:
        exam_key = exam_name.lower()
        if exam_key not in exam_dates:
            available_exams = ", ".join([exam['name'] for exam in exam_dates.values()])
            await interaction.response.send_message(f"❌ Exam '{exam_name}' not found. Available exams: {available_exams}", ephemeral=True)
            return
        
        exam_data = exam_dates[exam_key]
        exam_datetime = exam_data['datetime']
        time_until = exam_datetime - datetime.now()
        
        if time_until.total_seconds() <= 0:
            embed = discord.Embed(
                title="⏰ Exam Time!",
                description=f"**{exam_data['name']}** is happening now or has passed!",
                color=discord.Color.red()
            )
        else:
            days = time_until.days
            hours = int((time_until.total_seconds() % 86400) / 3600)
            minutes = int((time_until.total_seconds() % 3600) / 60)
            
            embed = discord.Embed(
                title="⏳ Exam Countdown",
                description=f"**{exam_data['name']}**\n<t:{int(exam_datetime.timestamp())}:F>",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Time Remaining:",
                value=f"**{days}** days, **{hours}** hours, **{minutes}** minutes",
                inline=False
            )
    else:
        # Show all exams
        embed = discord.Embed(
            title="📅 All Exam Countdowns",
            color=discord.Color.orange()
        )
        
        for exam_data in sorted(exam_dates.values(), key=lambda x: x['datetime']):
            exam_datetime = exam_data['datetime']
            time_until = exam_datetime - datetime.now()
            
            if time_until.total_seconds() <= 0:
                time_text = "**EXAM TIME!**"
            else:
                days = time_until.days
                time_text = f"{days} days remaining"
            
            embed.add_field(
                name=exam_data['name'],
                value=f"<t:{int(exam_datetime.timestamp())}:d>\n{time_text}",
                inline=True
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_exam", description="Remove an exam from countdown")
@app_commands.describe(exam_name="Name of the exam to remove")
async def remove_exam(interaction: discord.Interaction, exam_name: str):
    """Remove exam from countdown list"""
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You need 'Manage Channels' permission to remove exam dates.", ephemeral=True)
        return
    
    exam_key = exam_name.lower()
    if exam_key not in exam_dates:
        await interaction.response.send_message(f"❌ Exam '{exam_name}' not found.", ephemeral=True)
        return
    
    removed_exam = exam_dates.pop(exam_key)
    
    # Save exam dates to file
    save_exam_dates()
    
    embed = discord.Embed(
        title="🗑️ Exam Removed",
        description=f"**{removed_exam['name']}** has been removed from the countdown list.",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ib_boundaries", description="Show IB level boundaries for a subject")
@app_commands.describe(subject="Choose the subject")
@app_commands.choices(subject=[
    app_commands.Choice(name="Math SL", value="math_sl"),
    app_commands.Choice(name="Math HL", value="math_hl"),
    app_commands.Choice(name="General (Default)", value="default"),
])
async def ib_boundaries(interaction: discord.Interaction, subject: str):
    """Show the IB level boundaries for a specific subject"""
    if subject not in IB_LEVEL_BOUNDARIES:
        available_subjects = ", ".join(IB_LEVEL_BOUNDARIES.keys())
        await interaction.response.send_message(f"❌ Invalid subject. Available subjects: {available_subjects}", ephemeral=True)
        return
    
    boundaries = IB_LEVEL_BOUNDARIES[subject]
    
    embed = discord.Embed(
        title=f"📊 {subject.replace('_', ' ').title()} IB Level Boundaries",
        description="Converted Ontario percentages required for each IB level",
        color=discord.Color.purple()
    )
    
    # Create the boundaries table
    boundary_rows = []
    for level in range(1, 8):
        min_percent = boundaries[level]
        if level < 7:
            max_percent = boundaries[level + 1] - 1
            range_text = f"**Level {level}:** {min_percent}% - {max_percent}%"
        else:
            range_text = f"**Level {level}:** {min_percent}% - 100%"
        boundary_rows.append(range_text)
    
    embed.add_field(
        name="Level Boundaries:",
        value="\n".join(boundary_rows),
        inline=False
    )
    
    embed.set_footer(text="Based on WOSS IB standards")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ahhhh", description="Give everyone the Locked In role for 480 minutes (admin only)")
async def ahhhh(interaction: discord.Interaction):
    """Give everyone the Locked In role for 480 minutes (admin only)"""
    guild = interaction.guild
    admin_role = discord.utils.get(guild.roles, name="Admins")
    is_admin = admin_role in interaction.user.roles if admin_role else False
    if not is_admin:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only users with the 'Admins' role can use /AHHHH.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    focus_role_name = f"🔒 Locked In (Deep)"
    focus_role = discord.utils.get(guild.roles, name=focus_role_name)
    if not focus_role:
        await interaction.response.send_message("❌ The 'Locked In (Deep)' role does not exist. Please ask an admin to create it.", ephemeral=True)
        return
    count = 0
    for member in guild.members:
        if not member.bot:
            try:
                await member.add_roles(focus_role, reason="AHHHH command used by admin")
                # Set up a focus session for 480 minutes for each user
                end_time = datetime.now() + timedelta(minutes=480)
                focus_sessions[member.id] = {
                    'end_time': end_time,
                    'role': focus_role,
                    'mode': 'deep',
                    'duration': 480,
                    'user': member
                }
                count += 1
            except Exception:
                pass
    embed = discord.Embed(
        title="🔒 AHHHH! Everyone is now Locked In!",
        description=f"Gave the Locked In role to {count} users for 480 minutes.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_resource", description="Add a study resource to the resources channel")
@app_commands.describe(
    url="URL of the resource",
    description="Description of the resource",
    subject="Subject category for the resource"
)
@app_commands.choices(subject=[
    app_commands.Choice(name="Physics", value="physics"),
    app_commands.Choice(name="Chemistry", value="chemistry"),
    app_commands.Choice(name="Biology", value="biology"),
    app_commands.Choice(name="Math", value="math"),
    app_commands.Choice(name="English", value="english"),
    app_commands.Choice(name="French", value="french"),
    app_commands.Choice(name="Spanish", value="spanish"),
    app_commands.Choice(name="Geography", value="geography"),
    app_commands.Choice(name="History", value="history"),
    app_commands.Choice(name="Economics", value="economics"),
    app_commands.Choice(name="Business", value="business"),
    app_commands.Choice(name="General", value="general"),
])
async def add_resource(interaction: discord.Interaction, url: str, description: str, subject: str):
    """Add a study resource to the resources channel"""
    # Store the resource
    if subject not in resources:
        resources[subject] = []
    
    resources[subject].append({
        'url': url,
        'description': description,
        'added_by': interaction.user.display_name,
        'added_at': datetime.now().isoformat()
    })
    
    # Save resources to file
    save_resources()
    
    # Update the resources message
    await update_resources_message(interaction.guild)
    
    embed = discord.Embed(
        title="✅ Resource Added!",
        description=f"**Subject:** {subject.title()}\n**Description:** {description}\n**URL:** {url}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Added by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="refresh_resources", description="Refresh the resources message in the channel")
async def refresh_resources(interaction: discord.Interaction):
    """Refresh the resources message in the channel"""
    await update_resources_message(interaction.guild)
    
    embed = discord.Embed(
        title="✅ Resources Refreshed!",
        description="The resources message has been updated in the channel.",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_resources_message(guild):
    """Update the resources message in the specified channel"""
    channel_id = 1386860031512940565
    channel = guild.get_channel(channel_id)
    
    if not channel:
        print(f"Warning: Resources channel {channel_id} not found")
        return
    
    # Create the resources embed
    embed = discord.Embed(
        title="📚 Study Resources",
        description="Organized by subject - click the links to access the resources!",
        color=discord.Color.blue()
    )
    
    if not resources:
        embed.add_field(
            name="No Resources Yet",
            value="Be the first to add a resource using `/add_resource`!",
            inline=False
        )
    else:
        # Sort subjects alphabetically, but show general first
        subjects = sorted(resources.keys())
        if "general" in subjects:
            # Move general to the front
            subjects.remove("general")
            subjects = ["general"] + subjects
        
        for subject in subjects:
            subject_resources = resources[subject]
            
            # Create formatted list of resources for this subject
            resource_list = []
            for i, resource in enumerate(subject_resources, 1):
                resource_list.append(f"{i}. [{resource['description']}]({resource['url']}) - Added by {resource['added_by']}")
            
            # Join resources with newlines, limit to avoid field length issues
            resources_text = "\n".join(resource_list)
            if len(resources_text) > 1024:
                resources_text = resources_text[:1021] + "..."
            
            embed.add_field(
                name=f"📖 {subject.title()}",
                value=resources_text,
                inline=False
            )
    
    # Add instructions at the end
    embed.add_field(
        name="➕ How to Add Resources",
        value="Use `/add_resource <url> <description> <subject>` to add new study resources to this list!",
        inline=False
    )
    
    embed.set_footer(text="Last updated")
    embed.timestamp = datetime.now()
    
    # Try to find and update existing message, or send new one
    try:
        # Look for the bot's previous message in the channel
        async for message in channel.history(limit=100):
            if message.author == bot.user and "📚 Study Resources" in message.embeds[0].title if message.embeds else False:
                await message.edit(embed=embed)
                return
        
        # If no existing message found, send a new one
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error updating resources message: {e}")

# Background Tasks
@tasks.loop(minutes=1)
async def check_focus_sessions():
    """Check for expired focus sessions"""
    current_time = datetime.now()
    expired_sessions = []
    
    for user_id, session_data in focus_sessions.items():
        if current_time >= session_data['end_time']:
            expired_sessions.append(user_id)
    
    for user_id in expired_sessions:
        session_data = focus_sessions[user_id]
        user = session_data['user']
        
        # Remove focus session role
        try:
            await user.remove_roles(session_data['role'], reason="Focus session completed")
        except:
            pass
        
        # Send completion message
        try:
            embed = discord.Embed(
                title="⏰ Focus Session Complete!",
                description=f"Your **{session_data['duration']}-minute** focus session has ended.\n\nGreat work! 🌟",
                color=discord.Color.green()
            )
            embed.set_footer(text="Ready for another session? Use /focus to start again!")
            await user.send(embed=embed)
        except:
            pass
        
        # Remove from active sessions
        del focus_sessions[user_id]

@tasks.loop(hours=24)
async def update_exam_countdowns():
    """Daily update for exam countdowns"""
    # Remove past exams
    current_time = datetime.now()
    past_exams = []
    
    for exam_key, exam_data in exam_dates.items():
        if exam_data['datetime'] <= current_time:
            past_exams.append(exam_key)
    
    for exam_key in past_exams:
        del exam_dates[exam_key]
    
    # Save exam dates to file if any were removed
    if past_exams:
        save_exam_dates()

if __name__ == "__main__":
    # Make sure to set your bot token in .env file
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
    else:
        bot.run(token)
