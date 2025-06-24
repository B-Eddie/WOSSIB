# WOSSIB - IB Study Discord Bot

A Discord bot designed specifically for IB (International Baccalaureate) study servers. Features focus mode, IB score calculations, and exam countdown functionality.

## Features

### 🎯 Focus Mode
- **Start Focus Sessions**: `/focus duration mode` - Start a focus session with customizable duration and mode
- **Focus Status**: `/focus_status` - Check your current focus session status
- **End Focus**: `/unfocus` - Manually end your focus session
- **Automatic Role Management**: Assigns temporary focus roles that restrict access to distracting channels
- **Multiple Focus Modes**: Deep focus, study group, and subject-specific modes
- **Session Tracking**: Tracks actual vs planned study time

### 📊 IB Score Conversion
- **IB to Percentage**: `/ib_to_percent ib_grade` - Convert IB grades (1-7) to percentages
- **Percentage to IB**: `/percent_to_ib percentage` - Convert percentages to IB grades
- **Total Score Calculator**: `/calculate_total subject1 subject2 ... tok_ee_bonus` - Calculate total IB diploma score
- **Diploma Status**: Automatically determines if diploma requirements are met
- **Grade Distribution**: Shows breakdown of grades across subjects

### 📅 Exam Countdown
- **Set Exam Dates**: `/set_exam exam_name date time` - Set exam dates for countdown (requires Manage Channels permission)
- **View Countdowns**: `/exam_countdown [exam_name]` - View countdown to specific exam or all exams
- **Remove Exams**: `/remove_exam exam_name` - Remove exam from countdown list
- **Automatic Cleanup**: Past exams are automatically removed daily

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Discord bot token
- Server ID where the bot will be used

### 2. Installation
```bash
# Clone or download the project
cd WOSSIB

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file with your bot credentials:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_server_id_here
   ```

### 4. Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token to your `.env` file
4. Invite the bot to your server with the following permissions:
   - Manage Roles
   - Send Messages
   - Use Slash Commands
   - View Channels
   - Manage Channels (for exam management)

### 5. Running the Bot
```bash
python ib_bot.py
```

## Commands Reference

### Focus Mode Commands
- `/focus <duration> [mode]` - Start focus session (duration in minutes, max 480)
- `/unfocus` - End current focus session
- `/focus_status` - Check focus session status

**Focus Modes:**
- `deep` - Maximum restrictions, study resources only
- `study_group` - Access to study channels and voice rooms
- `subject` - Restricted to specific subject channels

### IB Score Commands
- `/ib_to_percent <ib_grade>` - Convert IB grade (1-7) to percentage
- `/percent_to_ib <percentage>` - Convert percentage (0-100) to IB grade
- `/calculate_total <sub1> <sub2> <sub3> <sub4> <sub5> <sub6> [tok_ee_bonus]` - Calculate total IB score

### Exam Management Commands
- `/set_exam <exam_name> <date> [time]` - Set exam date (YYYY-MM-DD format)
- `/exam_countdown [exam_name]` - View exam countdown(s)
- `/remove_exam <exam_name>` - Remove exam from list

## How It Works

### Focus Mode System
1. When a user starts a focus session, they receive a temporary role
2. The role restricts access to distracting channels (configured by server admins)
3. The bot automatically removes the role when the session ends
4. Users receive completion notifications with session statistics

### IB Score Conversion
- Uses standard IB grade boundaries for conversion
- Accounts for diploma requirements (minimum 24 points, no grade below 3)
- Includes TOK/EE bonus points calculation

### Exam Countdown
- Stores exam dates and provides real-time countdowns
- Automatically removes past exams
- Supports multiple exam tracking for the same grade level

## Customization

### Channel Restrictions
To set up channel restrictions for focus mode:
1. Create channels you want to restrict during focus mode
2. Modify channel permissions to deny access to focus mode roles
3. The bot will automatically assign these roles during focus sessions

### Role Permissions
The bot creates roles with the following naming pattern:
- `🎯 Focus Mode (Deep)`
- `🎯 Focus Mode (Study_group)`
- `🎯 Focus Mode (Subject)`

Configure channel permissions for these roles as needed.

## Data Storage
Currently uses in-memory storage. For production deployment, consider implementing:
- Database storage for persistent data
- User preference storage
- Session history tracking

## Support
This bot is designed for IB study servers where all users are in the same grade level. For multi-grade servers, additional role management may be needed.

## License
This project is open source. Feel free to modify and distribute as needed for your IB study community.
