import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=None, intents=intents)

# Data storage (in production, use a proper database)
focus_sessions = {}
exam_dates = {}

# IB Score conversion tables
IB_TO_PERCENTAGE = {
    7: 96, 6: 91, 5: 84, 4: 77, 3: 65, 2: 50, 1: 35
}

PERCENTAGE_TO_IB = {
    range(96, 101): 7,
    range(91, 96): 6,
    range(84, 91): 5,
    range(77, 84): 4,
    range(65, 77): 3,
    range(50, 65): 2,
    range(0, 50): 1
}

def percentage_to_ib(percentage):
    """Convert percentage to IB grade"""
    for grade_range, ib_grade in PERCENTAGE_TO_IB.items():
        if percentage in grade_range:
            return ib_grade
    return 1

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} guilds')
    
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')
    
    try:
        # Try to sync commands globally first
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global command(s)")
        
        # Also try to sync to specific guild if GUILD_ID is set
        guild_id = os.getenv('GUILD_ID')
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            bot.tree.copy_global_to(guild=guild)
            synced_guild = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced_guild)} command(s) to guild {guild_id}")
        
        # List all commands that were synced
        for command in synced:
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

# Focus Mode Commands
@bot.tree.command(name="focus", description="Start a focus session")
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
    focus_role_name = f"🎯 Focus Mode ({mode.title()})"
    focus_role = discord.utils.get(guild.roles, name=focus_role_name)
    
    if not focus_role:
        try:
            focus_role = await guild.create_role(
                name=focus_role_name,
                color=discord.Color.red(),
                reason="Focus mode role creation"
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create roles.", ephemeral=True)
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
        title="🎯 Focus Mode Activated!",
        description=f"**Mode:** {mode.title()}\n**Duration:** {duration} minutes\n**Ends at:** <t:{int(end_time.timestamp())}:t>",
        color=discord.Color.red()
    )
    embed.add_field(
        name="What's restricted:",
        value="• Casual chat channels\n• Meme channels\n• Gaming channels\n• Off-topic discussions",
        inline=False
    )
    embed.set_footer(text="Stay focused! You got this! 📚")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unfocus", description="End your current focus session")
async def unfocus(interaction: discord.Interaction):
    """End the current focus session"""
    user_id = interaction.user.id
    
    if user_id not in focus_sessions:
        await interaction.response.send_message("❌ You're not currently in a focus session.", ephemeral=True)
        return
    
    session_data = focus_sessions[user_id]
    
    # Remove role
    try:
        await interaction.user.remove_roles(session_data['role'], reason="Focus session ended manually")
    except discord.Forbidden:
        pass
    
    # Calculate session duration
    started_time = session_data['end_time'] - timedelta(minutes=session_data['duration'])
    actual_duration = datetime.now() - started_time
    actual_minutes = int(actual_duration.total_seconds() / 60)
    
    # Remove from active sessions
    del focus_sessions[user_id]
    
    embed = discord.Embed(
        title="✅ Focus Session Completed!",
        description=f"Great work! You focused for **{actual_minutes} minutes**",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Session Stats:",
        value=f"**Planned:** {session_data['duration']} minutes\n**Actual:** {actual_minutes} minutes\n**Mode:** {session_data['mode'].title()}",
        inline=False
    )
    embed.set_footer(text="Keep up the great work! 🌟")
    
    await interaction.response.send_message(embed=embed)

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

# IB Score Conversion Commands
@bot.tree.command(name="ib_to_percent", description="Convert IB grade to percentage")
async def ib_to_percent(interaction: discord.Interaction, ib_grade: int):
    """Convert IB grade (1-7) to percentage"""
    if ib_grade not in range(1, 8):
        await interaction.response.send_message("❌ IB grades must be between 1 and 7.", ephemeral=True)
        return
    
    percentage = IB_TO_PERCENTAGE[ib_grade]
    
    embed = discord.Embed(
        title="📊 IB Grade Conversion",
        description=f"**IB Grade {ib_grade}** = **{percentage}%**",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="percent_to_ib", description="Convert percentage to IB grade")
async def percent_to_ib(interaction: discord.Interaction, percentage: int):
    """Convert percentage to IB grade"""
    if percentage not in range(0, 101):
        await interaction.response.send_message("❌ Percentage must be between 0 and 100.", ephemeral=True)
        return
    
    ib_grade = percentage_to_ib(percentage)
    
    embed = discord.Embed(
        title="📊 Percentage Conversion",
        description=f"**{percentage}%** = **IB Grade {ib_grade}**",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="calculate_total", description="Calculate total IB score from individual grades")
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
    
    await interaction.response.send_message(embed=embed)

# Exam Countdown Commands
@bot.tree.command(name="set_exam", description="Set an exam date for countdown")
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
    
    embed = discord.Embed(
        title="🗑️ Exam Removed",
        description=f"**{removed_exam['name']}** has been removed from the countdown list.",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

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
        
        # Remove focus role
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

if __name__ == "__main__":
    # Make sure to set your bot token in .env file
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
    else:
        bot.run(token)
