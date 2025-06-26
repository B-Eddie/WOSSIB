# WOSSIB Discord Bot

A Discord bot designed for IB (International Baccalaureate) students with focus mode, grade conversion, and exam countdown features.

## Features

### 🎯 Focus Mode System

- **Focus Sessions**: Start timed focus sessions to stay productive
- **Role-Based Restrictions**: Get a focus role that restricts access to distracting channels
- **Visual Indicators**: Show you're in study mode with a focus role
- **Session Tracking**: Monitor your focus time and progress
- **Focus List**: See who else is currently in focus mode

### 📊 IB Grade Tools

- **Grade Conversion**: Convert between IB grades (1-7) and percentages
- **Score Calculator**: Calculate total IB diploma scores with TOK/EE bonus points
- **Grade Validation**: Ensure your grades meet diploma requirements

### 📅 Exam Management

- **Exam Countdown**: Set and track exam dates with countdown timers
- **Multiple Exams**: Manage multiple exams simultaneously
- **Time Reminders**: Get daily updates on exam countdowns

## Setup Instructions

### 1. Bot Setup

1. Create a Discord application and bot at https://discord.com/developers/applications
2. Invite the bot to your server with these permissions:
   - `applications.commands` (for slash commands)
   - `Manage Roles`
   - `Manage Channels`
   - `Send Messages`
   - `Read Message History`

### 2. Environment Variables

Create a `.env` file in the project root:

```
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here
```

### 3. Focus System Setup

1. **Configure channel permissions** to restrict focus mode roles from sending messages in distracting channels
2. **The bot will create focus roles** automatically when users start focus sessions
3. **Focus roles follow the pattern**: `🎯 Focus Mode (Deep)`, `🎯 Focus Mode (Study_group)`, etc.

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Bot

```bash
python ib_bot.py
```

## How Focus Mode Works

### For Users:

1. Use `/focus <duration> <mode>` to start a focus session (duration in minutes)
2. You'll get a focus role that restricts access to distracting channels
3. Use `/focus_status` to check remaining time
4. Use `/unfocus` to end early or wait for automatic completion
5. Use `/focus_list` to see who else is in focus mode

### Focus Modes:

- `deep` - Maximum restrictions, study resources only
- `study_group` - Access to study channels and voice rooms
- `subject` - Restricted to specific subject channels

## Commands

### Focus Commands

- `/focus <duration> <mode>` - Start a focus session (duration in minutes)
- `/unfocus` - End your current focus session
- `/focus_status` - Check session status
- `/focus_list` - Show all users currently in focus mode

### Grade Conversion

- `/ib_to_percent <grade>` - Convert IB grade to percentage
- `/percent_to_ib <percentage>` - Convert percentage to IB grade
- `/calculate_total <subjects...> <tok_ee_bonus>` - Calculate total IB score

### Exam Management

- `/set_exam <name> <date> <time>` - Set exam date (admin only)
- `/exam_countdown <name>` - Show countdown to exam
- `/remove_exam <name>` - Remove exam (admin only)

## Troubleshooting

### Duplicate Commands

- Make sure you have `GUILD_ID` set in your `.env` file
- The bot will only sync commands to the specific guild, preventing duplicates

### Focus Mode Not Working

- Ensure you've configured channel permissions to restrict focus roles from sending messages
- Focus roles are created automatically when users start sessions
- Check that the bot role is positioned above the roles it needs to manage

### Permission Errors

- Make sure the bot has the required permissions in your server
- Check that the bot role is positioned above the roles it needs to manage

## Support

For issues or questions, please check the troubleshooting section above or create an issue in the repository.
