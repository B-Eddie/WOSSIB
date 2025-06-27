import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
from discord import app_commands

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

# IB Score conversion tables - WOSS IB specific conversions
# Based on IB Conversions Master Document.csv

# Subject-specific raw to converted mark conversions
# Format: {raw_mark: ontario_percentage}
SUBJECT_CONVERSIONS = {
    "chemistry_sl": {
        0: 0, 1: 3, 2: 7, 3: 10, 4: 13, 5: 16, 6: 20, 7: 23, 8: 26, 9: 29, 10: 33, 11: 36, 12: 39, 13: 42, 14: 46, 15: 49,
        16: 50, 17: 51, 18: 52, 19: 53, 20: 54, 21: 55, 22: 56, 23: 57, 24: 58, 25: 59, 26: 60, 27: 59, 28: 60, 29: 61,
        30: 62, 31: 63, 32: 63, 33: 64, 34: 65, 35: 66, 36: 66, 37: 67, 38: 68, 39: 69, 40: 70, 41: 71, 42: 71, 43: 72,
        44: 73, 45: 74, 46: 75, 47: 76, 48: 77, 49: 78, 50: 79, 51: 80, 52: 81, 53: 82, 54: 83, 55: 84, 56: 85, 57: 86, 58: 87, 59: 88, 60: 88,
        61: 89, 62: 90, 63: 91, 64: 92, 65: 93, 66: 93, 67: 94, 68: 95, 69: 95, 70: 95, 71: 96, 72: 96, 73: 97, 74: 97, 75: 98, 76: 98, 77: 98, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 97, 84: 97, 85: 97, 86: 98, 87: 98, 88: 98, 89: 98, 90: 98, 91: 98, 92: 98, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "chemistry_hl": {
        0: 0, 1: 3, 2: 5, 3: 8, 4: 10, 5: 13, 6: 15, 7: 18, 8: 20, 9: 23, 10: 26, 11: 28, 12: 31, 13: 34, 14: 36, 15: 39, 16: 41, 17: 44, 18: 46, 19: 49,
        20: 50, 21: 51, 22: 51, 23: 52, 24: 53, 25: 53, 26: 54, 27: 54, 28: 55, 29: 56, 30: 56, 31: 57, 32: 58, 33: 58, 34: 59, 35: 59, 36: 60, 37: 61, 38: 62, 39: 63, 40: 64, 41: 64, 42: 65, 43: 66, 44: 67, 45: 68, 46: 69, 47: 69, 48: 70, 49: 71, 50: 72, 51: 73, 52: 74, 53: 75, 54: 76, 55: 78, 56: 79, 57: 80, 58: 81, 59: 82, 60: 83, 61: 84, 62: 85, 63: 86, 64: 87, 65: 88, 66: 88, 67: 89, 68: 90, 69: 91, 70: 92, 71: 93, 72: 93, 73: 94, 74: 95, 75: 95, 76: 96, 77: 96, 78: 96, 79: 96, 80: 96, 81: 96, 82: 97, 83: 97, 84: 97, 85: 97, 86: 97, 87: 97, 88: 98, 89: 98, 90: 98, 91: 98, 92: 98, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "biology_sl": {
        0: 0, 1: 3, 2: 7, 3: 10, 4: 13, 5: 16, 6: 20, 7: 23, 8: 26, 9: 29, 10: 33, 11: 36, 12: 39, 13: 42, 14: 46, 15: 49,
        16: 50, 17: 51, 18: 52, 19: 52, 20: 53, 21: 54, 22: 55, 23: 55, 24: 56, 25: 57, 26: 58, 27: 58, 28: 59, 29: 60, 30: 61, 31: 62, 32: 62, 33: 63, 34: 64, 35: 65, 36: 65, 37: 66, 38: 67, 39: 67, 40: 68, 41: 69, 42: 70, 43: 70, 44: 71, 45: 72, 46: 73, 47: 74, 48: 74, 49: 75, 50: 76, 51: 77, 52: 78, 53: 78, 54: 79, 55: 80, 56: 81, 57: 81, 58: 82, 59: 83, 60: 84, 61: 85, 62: 86, 63: 87, 64: 88, 65: 88, 66: 89, 67: 90, 68: 91, 69: 92, 70: 93, 71: 93, 72: 94, 73: 94, 74: 94, 75: 95, 76: 95, 77: 95, 78: 96, 79: 96, 80: 97, 81: 97, 82: 97, 83: 97, 84: 97, 85: 97, 86: 97, 87: 98, 88: 98, 89: 98, 90: 98, 91: 98, 92: 98, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "biology_hl": {
        0: 0, 1: 3, 2: 7, 3: 10, 4: 13, 5: 16, 6: 20, 7: 23, 8: 26, 9: 29, 10: 33, 11: 36, 12: 39, 13: 42, 14: 46, 15: 49,
        16: 50, 17: 51, 18: 52, 19: 52, 20: 53, 21: 54, 22: 55, 23: 55, 24: 56, 25: 57, 26: 58, 27: 58, 28: 59, 29: 60, 30: 61, 31: 62, 32: 62, 33: 63, 34: 64, 35: 65, 36: 65, 37: 66, 38: 67, 39: 67, 40: 68, 41: 69, 42: 70, 43: 70, 44: 71, 45: 72, 46: 73, 47: 74, 48: 74, 49: 75, 50: 76, 51: 77, 52: 78, 53: 78, 54: 79, 55: 80, 56: 81, 57: 81, 58: 82, 59: 83, 60: 84, 61: 85, 62: 85, 63: 86, 64: 87, 65: 88, 66: 88, 67: 89, 68: 90, 69: 91, 70: 91, 71: 92, 72: 93, 73: 94, 74: 95, 75: 95, 76: 96, 77: 96, 78: 96, 79: 96, 80: 96, 81: 97, 82: 97, 83: 97, 84: 97, 85: 97, 86: 97, 87: 98, 88: 98, 89: 98, 90: 98, 91: 98, 92: 98, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "physics_sl": {
        0: 0, 1: 4, 2: 7, 3: 11, 4: 14, 5: 18, 6: 21, 7: 25, 8: 28, 9: 32, 10: 35, 11: 39, 12: 42, 13: 46, 14: 49,
        15: 50, 16: 51, 17: 52, 18: 53, 19: 54, 20: 55, 21: 56, 22: 57, 23: 58, 24: 59, 25: 60, 26: 61, 27: 62, 28: 63, 29: 64, 30: 65, 31: 66, 32: 67, 33: 68, 34: 69, 35: 70, 36: 71, 37: 72, 38: 73, 39: 74, 40: 75, 41: 76, 42: 77, 43: 78, 44: 78, 45: 79, 46: 80, 47: 81, 48: 82, 49: 83, 50: 84, 51: 85, 52: 86, 53: 87, 54: 88, 55: 88, 56: 89, 57: 90, 58: 91, 59: 92, 60: 93, 61: 93, 62: 94, 63: 94, 64: 94, 65: 95, 66: 95, 67: 95, 68: 96, 69: 96, 70: 97, 71: 97, 72: 97, 73: 97, 74: 97, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 98, 81: 98, 82: 98, 83: 98, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "geography_hl": {
        0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 25, 7: 29, 8: 33, 9: 37, 10: 41, 11: 45, 12: 49,
        13: 50, 14: 51, 15: 51, 16: 52, 17: 53, 18: 53, 19: 54, 20: 55, 21: 55, 22: 56, 23: 57, 24: 57, 25: 58, 26: 59, 27: 59, 28: 60, 29: 61, 30: 62, 31: 63, 32: 63, 33: 64, 34: 65, 35: 66, 36: 66, 37: 67, 38: 68, 39: 69, 40: 69, 41: 70, 42: 71, 43: 72, 44: 73, 45: 74, 46: 76, 47: 77, 48: 78, 49: 79, 50: 81, 51: 82, 52: 83, 53: 84, 54: 85, 55: 86, 56: 86, 57: 87, 58: 88, 59: 89, 60: 90, 61: 90, 62: 91, 63: 92, 64: 93, 65: 93, 66: 94, 67: 94, 68: 94, 69: 95, 70: 95, 71: 95, 72: 95, 73: 96, 74: 96, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 98, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 99, 97: 100, 98: 100, 99: 100, 100: 100
    },
    "french_sl": {
        0: 40, 1: 41, 2: 41, 3: 42, 4: 43, 5: 43, 6: 44, 7: 45, 8: 45, 9: 46, 10: 46, 11: 47, 12: 48, 13: 48, 14: 49,
        15: 50, 16: 51, 17: 51, 18: 52, 19: 53, 20: 53, 21: 54, 22: 55, 23: 55, 24: 56, 25: 57, 26: 57, 27: 58, 28: 59, 29: 60, 30: 60, 31: 61, 32: 62, 33: 63, 34: 63, 35: 64, 36: 65, 37: 66, 38: 66, 39: 67, 40: 68, 41: 69, 42: 69, 43: 70, 44: 71, 45: 72, 46: 73, 47: 74, 48: 74, 49: 75, 50: 76, 51: 77, 52: 78, 53: 78, 54: 79, 55: 80, 56: 81, 57: 81, 58: 82, 59: 83, 60: 84, 61: 84, 62: 85, 63: 85, 64: 85, 65: 86, 66: 86, 67: 87, 68: 88, 69: 89, 70: 90, 71: 91, 72: 92, 73: 92, 74: 93, 75: 94, 76: 94, 77: 95, 78: 95, 79: 95, 80: 95, 81: 96, 82: 96, 83: 96, 84: 97, 85: 97, 86: 97, 87: 97, 88: 97, 89: 97, 90: 97, 91: 98, 92: 98, 93: 98, 94: 98, 95: 99, 96: 99, 97: 99, 98: 100, 99: 100, 100: 100
    },
    "french_hl": {
        0: 40, 1: 41, 2: 41, 3: 42, 4: 42, 5: 43, 6: 44, 7: 44, 8: 45, 9: 45, 10: 46, 11: 47, 12: 47, 13: 48, 14: 48, 15: 49,
        16: 50, 17: 51, 18: 51, 19: 52, 20: 53, 21: 53, 22: 54, 23: 55, 24: 56, 25: 56, 26: 57, 27: 58, 28: 59, 29: 59, 30: 60, 31: 61, 32: 62, 33: 62, 34: 63, 35: 63, 36: 64, 37: 64, 38: 65, 39: 65, 40: 66, 41: 67, 42: 67, 43: 68, 44: 68, 45: 69, 46: 69, 47: 70, 48: 70, 49: 71, 50: 72, 51: 73, 52: 74, 53: 75, 54: 76, 55: 77, 56: 78, 57: 78, 58: 79, 59: 80, 60: 81, 61: 82, 62: 83, 63: 84, 64: 85, 65: 85, 66: 86, 67: 87, 68: 88, 69: 89, 70: 90, 71: 91, 72: 92, 73: 93, 74: 93, 75: 94, 76: 94, 77: 95, 78: 95, 79: 95, 80: 95, 81: 96, 82: 96, 83: 96, 84: 97, 85: 97, 86: 97, 87: 97, 88: 97, 89: 97, 90: 97, 91: 98, 92: 98, 93: 98, 94: 98, 95: 99, 96: 99, 97: 99, 98: 100, 99: 100, 100: 100
    },
    "english_hl": {
        0: 0, 1: 3, 2: 5, 3: 8, 4: 10, 5: 13, 6: 15, 7: 18, 8: 21, 9: 23, 10: 26, 11: 28, 12: 31, 13: 34, 14: 36, 15: 39, 16: 41, 17: 44, 18: 46, 19: 49,
        20: 50, 21: 51, 22: 51, 23: 52, 24: 53, 25: 53, 26: 54, 27: 55, 28: 55, 29: 56, 30: 57, 31: 57, 32: 58, 33: 59, 34: 59, 35: 60, 36: 61, 37: 62, 38: 63, 39: 64, 40: 65, 41: 67, 42: 68, 43: 69, 44: 70, 45: 71, 46: 72, 47: 73, 48: 74, 49: 75, 50: 76, 51: 77, 52: 78, 53: 79, 54: 80, 55: 81, 56: 81, 57: 82, 58: 83, 59: 83, 60: 84, 61: 85, 62: 85, 63: 86, 64: 87, 65: 87, 66: 88, 67: 89, 68: 90, 69: 91, 70: 92, 71: 92, 72: 93, 73: 94, 74: 94, 75: 95, 76: 95, 77: 95, 78: 95, 79: 96, 80: 96, 81: 96, 82: 96, 83: 97, 84: 97, 85: 97, 86: 97, 87: 97, 88: 97, 89: 97, 90: 97, 91: 98, 92: 98, 93: 98, 94: 98, 95: 98, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "math_sl": {
        0: 0, 1: 3, 2: 6, 3: 9, 4: 12, 5: 15, 6: 18, 7: 21, 8: 25, 9: 28, 10: 31, 11: 34, 12: 37, 13: 40, 14: 43, 15: 46, 16: 49,
        17: 50, 18: 51, 19: 51, 20: 52, 21: 53, 22: 53, 23: 54, 24: 54, 25: 55, 26: 56, 27: 56, 28: 57, 29: 58, 30: 58, 31: 59, 32: 59, 33: 60, 34: 61, 35: 62, 36: 62, 37: 63, 38: 64, 39: 65, 40: 66, 41: 66, 42: 67, 43: 68, 44: 69, 45: 69, 46: 70, 47: 71, 48: 72, 49: 73, 50: 74, 51: 75, 52: 76, 53: 77, 54: 78, 55: 79, 56: 80, 57: 81, 58: 82, 59: 83, 60: 84, 61: 85, 62: 86, 63: 87, 64: 88, 65: 88, 66: 89, 67: 90, 68: 90, 69: 91, 70: 92, 71: 93, 72: 93, 73: 94, 74: 94, 75: 95, 76: 95, 77: 96, 78: 96, 79: 96, 80: 96, 81: 97, 82: 97, 83: 97, 84: 97, 85: 97, 86: 97, 87: 97, 88: 97, 89: 98, 90: 98, 91: 98, 92: 98, 93: 98, 94: 98, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "math_hl": {
        0: 0, 1: 4, 2: 8, 3: 11, 4: 15, 5: 19, 6: 23, 7: 26, 8: 30, 9: 34, 10: 38, 11: 41, 12: 45, 13: 49,
        14: 50, 15: 51, 16: 51, 17: 52, 18: 53, 19: 54, 20: 54, 21: 55, 22: 56, 23: 56, 24: 57, 25: 58, 26: 59, 27: 59, 28: 60, 29: 61, 30: 62, 31: 63, 32: 64, 33: 65, 34: 66, 35: 66, 36: 67, 37: 68, 38: 69, 39: 70, 40: 71, 41: 72, 42: 73, 43: 74, 44: 75, 45: 76, 46: 77, 47: 78, 48: 79, 49: 80, 50: 81, 51: 82, 52: 83, 53: 84, 54: 85, 55: 85, 56: 86, 57: 87, 58: 88, 59: 88, 60: 89, 61: 90, 62: 91, 63: 91, 64: 92, 65: 93, 66: 93, 67: 94, 68: 94, 69: 95, 70: 95, 71: 96, 72: 96, 73: 96, 74: 96, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 97, 84: 97, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 98, 91: 98, 92: 98, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "economics_hl": {
        0: 0, 1: 4, 2: 7, 3: 11, 4: 14, 5: 18, 6: 21, 7: 25, 8: 28, 9: 32, 10: 35, 11: 39, 12: 42, 13: 46, 14: 49,
        15: 50, 16: 50, 17: 51, 18: 51, 19: 52, 20: 53, 21: 54, 22: 55, 23: 56, 24: 57, 25: 58, 26: 59, 27: 60, 28: 61, 29: 62, 30: 63, 31: 64, 32: 65, 33: 66, 34: 67, 35: 68, 36: 69, 37: 70, 38: 71, 39: 72, 40: 73, 41: 74, 42: 72, 43: 73, 44: 74, 45: 75, 46: 76, 47: 77, 48: 78, 49: 79, 50: 84, 51: 84, 52: 85, 53: 85, 54: 86, 55: 86, 56: 87, 57: 87, 58: 88, 59: 88, 60: 89, 61: 93, 62: 93, 63: 93, 64: 93, 65: 94, 66: 94, 67: 94, 68: 95, 69: 95, 70: 95, 71: 96, 72: 96, 73: 96, 74: 97, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 97, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 100, 97: 100, 98: 100, 99: 100, 100: 100
    },
    "physics_hl": {
        0: 0, 1: 4, 2: 7, 3: 11, 4: 14, 5: 18, 6: 21, 7: 25, 8: 28, 9: 32, 10: 35, 11: 39, 12: 42, 13: 46, 14: 49,
        15: 50, 16: 51, 17: 52, 18: 53, 19: 54, 20: 55, 21: 56, 22: 57, 23: 58, 24: 59, 25: 60, 26: 61, 27: 62, 28: 63, 29: 64, 30: 65, 31: 66, 32: 67, 33: 68, 34: 69, 35: 70, 36: 71, 37: 72, 38: 73, 39: 74, 40: 75, 41: 76, 42: 77, 43: 78, 44: 78, 45: 79, 46: 80, 47: 81, 48: 82, 49: 83, 50: 84, 51: 85, 52: 86, 53: 87, 54: 88, 55: 88, 56: 89, 57: 90, 58: 91, 59: 92, 60: 93, 61: 93, 62: 94, 63: 94, 64: 94, 65: 95, 66: 95, 67: 95, 68: 96, 69: 96, 70: 97, 71: 97, 72: 97, 73: 97, 74: 97, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 98, 81: 98, 82: 98, 83: 98, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "english_sl": {
        0: 0, 1: 3, 2: 5, 3: 8, 4: 10, 5: 13, 6: 15, 7: 18, 8: 21, 9: 23, 10: 26, 11: 28, 12: 31, 13: 34, 14: 36, 15: 39, 16: 41, 17: 44, 18: 46, 19: 49,
        20: 50, 21: 51, 22: 51, 23: 52, 24: 53, 25: 53, 26: 54, 27: 55, 28: 55, 29: 56, 30: 57, 31: 57, 32: 58, 33: 59, 34: 59, 35: 60, 36: 61, 37: 62, 38: 63, 39: 64, 40: 65, 41: 67, 42: 68, 43: 69, 44: 70, 45: 71, 46: 72, 47: 73, 48: 74, 49: 75, 50: 76, 51: 77, 52: 78, 53: 79, 54: 80, 55: 81, 56: 81, 57: 82, 58: 83, 59: 83, 60: 84, 61: 85, 62: 85, 63: 86, 64: 87, 65: 87, 66: 88, 67: 89, 68: 90, 69: 91, 70: 92, 71: 92, 72: 93, 73: 94, 74: 94, 75: 95, 76: 95, 77: 95, 78: 95, 79: 96, 80: 96, 81: 96, 82: 96, 83: 97, 84: 97, 85: 97, 86: 97, 87: 97, 88: 97, 89: 97, 90: 97, 91: 98, 92: 98, 93: 98, 94: 98, 95: 98, 96: 99, 97: 99, 98: 99, 99: 99, 100: 100
    },
    "geography_sl": {
        0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 25, 7: 29, 8: 33, 9: 37, 10: 41, 11: 45, 12: 49,
        13: 50, 14: 51, 15: 51, 16: 52, 17: 53, 18: 53, 19: 54, 20: 55, 21: 55, 22: 56, 23: 57, 24: 57, 25: 58, 26: 59, 27: 59, 28: 60, 29: 61, 30: 62, 31: 63, 32: 63, 33: 64, 34: 65, 35: 66, 36: 66, 37: 67, 38: 68, 39: 69, 40: 69, 41: 70, 42: 71, 43: 72, 44: 73, 45: 74, 46: 76, 47: 77, 48: 78, 49: 79, 50: 81, 51: 82, 52: 83, 53: 84, 54: 85, 55: 86, 56: 86, 57: 87, 58: 88, 59: 89, 60: 90, 61: 90, 62: 91, 63: 92, 64: 93, 65: 93, 66: 94, 67: 94, 68: 94, 69: 95, 70: 95, 71: 95, 72: 95, 73: 96, 74: 96, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 98, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 99, 97: 100, 98: 100, 99: 100, 100: 100
    },
    "history_hl": {
        0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 25, 7: 29, 8: 33, 9: 37, 10: 41, 11: 45, 12: 49,
        13: 50, 14: 51, 15: 51, 16: 52, 17: 53, 18: 53, 19: 54, 20: 55, 21: 55, 22: 56, 23: 57, 24: 57, 25: 58, 26: 59, 27: 59, 28: 60, 29: 61, 30: 62, 31: 63, 32: 63, 33: 64, 34: 65, 35: 66, 36: 66, 37: 67, 38: 68, 39: 69, 40: 69, 41: 70, 42: 71, 43: 72, 44: 73, 45: 74, 46: 76, 47: 77, 48: 78, 49: 79, 50: 81, 51: 82, 52: 83, 53: 84, 54: 85, 55: 86, 56: 86, 57: 87, 58: 88, 59: 89, 60: 90, 61: 90, 62: 91, 63: 92, 64: 93, 65: 93, 66: 94, 67: 94, 68: 94, 69: 95, 70: 95, 71: 95, 72: 95, 73: 96, 74: 96, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 98, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 99, 97: 100, 98: 100, 99: 100, 100: 100
    },
    "history_sl": {
        0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 25, 7: 29, 8: 33, 9: 37, 10: 41, 11: 45, 12: 49,
        13: 50, 14: 51, 15: 51, 16: 52, 17: 53, 18: 53, 19: 54, 20: 55, 21: 55, 22: 56, 23: 57, 24: 57, 25: 58, 26: 59, 27: 59, 28: 60, 29: 61, 30: 62, 31: 63, 32: 63, 33: 64, 34: 65, 35: 66, 36: 66, 37: 67, 38: 68, 39: 69, 40: 69, 41: 70, 42: 71, 43: 72, 44: 73, 45: 74, 46: 76, 47: 77, 48: 78, 49: 79, 50: 81, 51: 82, 52: 83, 53: 84, 54: 85, 55: 86, 56: 86, 57: 87, 58: 88, 59: 89, 60: 90, 61: 90, 62: 91, 63: 92, 64: 93, 65: 93, 66: 94, 67: 94, 68: 94, 69: 95, 70: 95, 71: 95, 72: 95, 73: 96, 74: 96, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 98, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 99, 97: 100, 98: 100, 99: 100, 100: 100
    },
    "economics_sl": {
        0: 0, 1: 4, 2: 7, 3: 11, 4: 14, 5: 18, 6: 21, 7: 25, 8: 28, 9: 32, 10: 35, 11: 39, 12: 42, 13: 46, 14: 49,
        15: 50, 16: 50, 17: 51, 18: 51, 19: 52, 20: 53, 21: 54, 22: 55, 23: 56, 24: 57, 25: 58, 26: 59, 27: 60, 28: 61, 29: 62, 30: 63, 31: 64, 32: 65, 33: 66, 34: 67, 35: 68, 36: 69, 37: 70, 38: 71, 39: 72, 40: 73, 41: 74, 42: 72, 43: 73, 44: 74, 45: 75, 46: 76, 47: 77, 48: 78, 49: 79, 50: 84, 51: 84, 52: 85, 53: 85, 54: 86, 55: 86, 56: 87, 57: 87, 58: 88, 59: 88, 60: 89, 61: 93, 62: 93, 63: 93, 64: 93, 65: 94, 66: 94, 67: 94, 68: 95, 69: 95, 70: 95, 71: 96, 72: 96, 73: 96, 74: 97, 75: 97, 76: 97, 77: 97, 78: 97, 79: 97, 80: 97, 81: 97, 82: 97, 83: 97, 84: 98, 85: 98, 86: 98, 87: 98, 88: 98, 89: 98, 90: 99, 91: 99, 92: 99, 93: 99, 94: 99, 95: 99, 96: 100, 97: 100, 98: 100, 99: 100, 100: 100
    }
}

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

def raw_to_converted(raw_percentage, subject="physics_sl"):
    """Convert raw IB mark to converted Ontario mark"""
    if subject not in SUBJECT_CONVERSIONS:
        subject = "physics_sl"  # Default fallback
    
    conversions = SUBJECT_CONVERSIONS[subject]
    
    # If exact match exists, return it
    if raw_percentage in conversions:
        return conversions[raw_percentage]
    
    # Find the two closest conversion points for interpolation
    raw_points = sorted(conversions.keys())
    
    # Handle edge cases
    if raw_percentage <= raw_points[0]:
        return conversions[raw_points[0]]
    if raw_percentage >= raw_points[-1]:
        return conversions[raw_points[-1]]
    
    # Find the two points to interpolate between
    for i in range(len(raw_points) - 1):
        if raw_points[i] <= raw_percentage <= raw_points[i + 1]:
            x1, x2 = raw_points[i], raw_points[i + 1]
            y1, y2 = conversions[x1], conversions[x2]
            
            # Linear interpolation
            converted = y1 + (y2 - y1) * (raw_percentage - x1) / (x2 - x1)
            return round(converted)
    
    # Fallback
    return conversions[raw_points[0]]

def ib_level_to_percentage(ib_level, subject="physics_sl"):
    """Convert IB level (1-7) to Ontario percentage using subject-specific conversions"""
    if subject not in SUBJECT_CONVERSIONS:
        subject = "physics_sl"  # Default fallback
    
    # The CSV shows IB levels mapping to Ontario percentages
    # We need to find the minimum percentage for each IB level
    conversions = SUBJECT_CONVERSIONS[subject]
    
    # For each IB level, find the minimum raw mark that gives that level
    # This is a simplified approach - in reality, we'd need the actual IB level boundaries
    # For now, we'll use the boundaries from IB_LEVEL_BOUNDARIES
    if subject in IB_LEVEL_BOUNDARIES:
        boundaries = IB_LEVEL_BOUNDARIES[subject]
    else:
        boundaries = IB_LEVEL_BOUNDARIES["default"]
    
    return boundaries[ib_level]

def percentage_to_ib_level(percentage, subject="physics_sl"):
    """Convert Ontario percentage to IB level using subject-specific boundaries"""
    # Get the appropriate boundaries for the subject
    if subject in IB_LEVEL_BOUNDARIES:
        boundaries = IB_LEVEL_BOUNDARIES[subject]
    else:
        boundaries = IB_LEVEL_BOUNDARIES["default"]
    
    # Find the appropriate level
    for level in range(7, 0, -1):
        if percentage >= boundaries[level]:
            return level
    return 1

def raw_to_ib_level(raw_percentage, subject="physics_sl"):
    """Convert raw IB mark directly to IB level"""
    converted = raw_to_converted(raw_percentage, subject)
    return percentage_to_ib_level(converted, subject)

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
    app_commands.Choice(name="Geography", value="geography"),
    app_commands.Choice(name="History", value="history"),
    app_commands.Choice(name="Economics", value="economics"),
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
    
    # Remove focus session role
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

@bot.tree.command(name="focus_list", description="Show all users currently in focus mode")
async def focus_list(interaction: discord.Interaction):
    """Show all users currently in focus mode"""
    if not focus_sessions:
        embed = discord.Embed(
            title="🎯 Focus Mode Status",
            description="No users are currently in focus mode.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="🎯 Users in Focus Mode",
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
    app_commands.Choice(name="Geography SL", value="geography_sl"),
    app_commands.Choice(name="Geography HL", value="geography_hl"),
    app_commands.Choice(name="History SL", value="history_sl"),
    app_commands.Choice(name="History HL", value="history_hl"),
    app_commands.Choice(name="Economics SL", value="economics_sl"),
    app_commands.Choice(name="Economics HL", value="economics_hl"),
])
async def raw_to_converted_cmd(interaction: discord.Interaction, raw_mark: int, subject: str):
    """Convert raw IB mark to Ontario percentage"""
    if raw_mark not in range(0, 101):
        await interaction.response.send_message("❌ Raw mark must be between 0 and 100.", ephemeral=True)
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
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ib_to_percent", description="Convert IB grade to percentage")
@app_commands.describe(
    ib_grade="IB grade (1-7)",
    subject="Choose the subject (optional)"
)
@app_commands.choices(subject=[
    app_commands.Choice(name="General (Default)", value="default"),
    app_commands.Choice(name="Math SL", value="math_sl"),
    app_commands.Choice(name="Math HL", value="math_hl"),
])
async def ib_to_percent(interaction: discord.Interaction, ib_grade: int, subject: str = "default"):
    """Convert IB grade (1-7) to percentage"""
    if ib_grade not in range(1, 8):
        await interaction.response.send_message("❌ IB grades must be between 1 and 7.", ephemeral=True)
        return
    
    # Get the appropriate boundaries for the subject
    if subject in IB_LEVEL_BOUNDARIES:
        boundaries = IB_LEVEL_BOUNDARIES[subject]
        subject_name = subject.replace('_', ' ').title()
    else:
        boundaries = IB_LEVEL_BOUNDARIES["default"]
        subject_name = "General"
    
    # Use the IB level boundaries to get the minimum percentage for each level
    percentage = boundaries[ib_grade]
    
    embed = discord.Embed(
        title="📊 IB Grade Conversion",
        description=f"**IB Grade {ib_grade}** = **{percentage}%** (minimum)\n**Subject:** {subject_name}",
        color=discord.Color.blue()
    )
    
    # Show the range for this level
    if ib_grade < 7:
        next_level_min = boundaries[ib_grade + 1]
        embed.add_field(
            name="Level Range:",
            value=f"**{percentage}% - {next_level_min - 1}%**",
            inline=False
        )
    else:
        embed.add_field(
            name="Level Range:",
            value=f"**{percentage}% - 100%**",
            inline=False
        )
    
    embed.add_field(
        name="Note:",
        value="This shows the minimum converted percentage required for each IB level. Actual raw marks vary by subject.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="percent_to_ib", description="Convert percentage to IB grade")
@app_commands.describe(
    percentage="Ontario percentage (0-100)",
    subject="Choose the subject (optional)"
)
@app_commands.choices(subject=[
    app_commands.Choice(name="General (Default)", value="default"),
    app_commands.Choice(name="Math SL", value="math_sl"),
    app_commands.Choice(name="Math HL", value="math_hl"),
])
async def percent_to_ib(interaction: discord.Interaction, percentage: int, subject: str = "default"):
    """Convert percentage to IB grade"""
    if percentage not in range(0, 101):
        await interaction.response.send_message("❌ Percentage must be between 0 and 100.", ephemeral=True)
        return
    
    ib_grade = percentage_to_ib_level(percentage, subject)
    
    # Get subject name
    if subject in IB_LEVEL_BOUNDARIES:
        subject_name = subject.replace('_', ' ').title()
    else:
        subject_name = "General"
    
    embed = discord.Embed(
        title="📊 Percentage Conversion",
        description=f"**{percentage}%** = **IB Grade {ib_grade}**\n**Subject:** {subject_name}",
        color=discord.Color.blue()
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
    app_commands.Choice(name="Geography SL", value="geography_sl"),
    app_commands.Choice(name="Geography HL", value="geography_hl"),
    app_commands.Choice(name="History SL", value="history_sl"),
    app_commands.Choice(name="History HL", value="history_hl"),
    app_commands.Choice(name="Economics SL", value="economics_sl"),
    app_commands.Choice(name="Economics HL", value="economics_hl"),
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
    languages = [s for s in SUBJECT_CONVERSIONS.keys() if any(subj in s for subj in ['english', 'french'])]
    humanities = [s for s in SUBJECT_CONVERSIONS.keys() if any(subj in s for subj in ['geography', 'history', 'economics'])]
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

if __name__ == "__main__":
    # Make sure to set your bot token in .env file
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
    else:
        bot.run(token)
