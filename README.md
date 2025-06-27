# WOSS IB Discord Bot

A comprehensive Discord bot designed specifically for WOSS IB students, featuring focus mode, exam countdowns, and accurate IB grade conversions based on official WOSS IB conversion tables.

## Features

### 🎯 Focus Mode

- **Start focus sessions** with customizable duration (up to 8 hours)
- **Subject-specific focus modes** (Physics, Chemistry, Biology, Math, English, French, Geography, History, Economics)
- **Automatic role assignment** to restrict access to casual channels
- **Session tracking** with automatic completion notifications
- **Focus status checking** and session management

### 📊 IB Grade Conversions

- **Accurate WOSS IB conversion tables** based on official school data
- **Subject-specific conversions** for all IB subjects (SL and HL)
- **Raw mark to Ontario percentage** conversion
- **IB level to percentage** conversion (1-7 scale)
- **Percentage to IB level** conversion
- **Complete conversion tables** for each subject

### 📅 Exam Countdown

- **Set exam dates** with custom names and times
- **Real-time countdown** to upcoming exams
- **Multiple exam tracking** with priority sorting
- **Automatic cleanup** of past exams

### 🎓 IB Diploma Calculator

- **Calculate total IB score** from individual subject grades
- **TOK/EE bonus points** inclusion
- **Diploma status** determination
- **Grade distribution** analysis

## Commands

### Focus Mode Commands

- `/focus <duration> <mode>` - Start a focus session
- `/unfocus` - End your current focus session
- `/focus_status` - Check your focus session status
- `/focus_list` - Show all users currently in focus mode

### IB Conversion Commands

- `/raw_to_converted <raw_mark> <subject>` - Convert raw IB mark to Ontario percentage
- `/ib_to_percent <ib_grade> <subject>` - Convert IB grade (1-7) to percentage
- `/percent_to_ib <percentage> <subject>` - Convert percentage to IB grade
- `/subject_conversion <subject>` - Show conversion table for a specific subject
- `/list_subjects` - List all available subjects for conversion
- `/ib_boundaries <subject>` - Show IB level boundaries for a subject

### Exam Commands

- `/set_exam <exam_name> <date> <time>` - Set an exam date for countdown
- `/exam_countdown <exam_name>` - Show countdown to specific exam
- `/remove_exam <exam_name>` - Remove an exam from countdown

### Diploma Calculator

- `/calculate_total <subject1> <subject2> ... <subject6> <tok_ee_bonus>` - Calculate total IB diploma score

## Supported Subjects

### Sciences

- Physics (SL/HL)
- Chemistry (SL/HL)
- Biology (SL/HL)

### Languages

- English (SL/HL)
- French (SL/HL)

### Humanities

- Geography (SL/HL)
- History (SL/HL)
- Economics (SL/HL)

### Mathematics

- Mathematics (SL/HL)

## Conversion System

The bot uses **official WOSS IB conversion tables** from the school's master document, ensuring accurate grade conversions that reflect the actual standards used at WOSS.

### IB Level Boundaries

- **Level 1:** 0-49%
- **Level 2:** 50-60%
- **Level 3:** 61-71%
- **Level 4:** 72-83%
- **Level 5:** 84-92%
- **Level 6:** 93-96%
- **Level 7:** 97-100%

_Note: Some subjects may have different boundaries (e.g., Math SL/HL have specific boundaries)_

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** with your Discord bot token:

   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

3. **Invite the bot** to your server with the following permissions:

   - `applications.commands` (for slash commands)
   - `Manage Roles` (for focus mode)
   - `Send Messages`
   - `Use Slash Commands`

4. **Run the bot:**
   ```bash
   python ib_bot.py
   ```

## Bot Permissions

Make sure to invite the bot with the correct scopes:

- **Bot scope** for basic functionality
- **applications.commands scope** for slash commands

## Focus Mode Features

When a user starts a focus session:

- A **red role** is assigned with the subject name
- Access to casual channels is restricted
- **Automatic completion** after the set duration
- **Session statistics** tracking

## Technical Details

- **Python 3.8+** required
- **Discord.py** with slash command support
- **Background tasks** for session management
- **Real-time updates** for exam countdowns
- **Subject-specific conversion tables** for accurate grade conversions

## Contributing

This bot is specifically designed for WOSS IB students. If you're a WOSS student and want to contribute:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues or questions specific to WOSS IB, please contact the bot administrator or create an issue in the repository.
