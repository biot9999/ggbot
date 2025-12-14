# Single File Deployment Option

## Overview
This project is currently organized as a modular Python application with separate files for better maintainability. However, if you need a single-file deployment, follow the instructions below.

## Current Structure (Recommended)
The modular structure provides:
- Better code organization
- Easier debugging and maintenance
- Clear separation of concerns  
- Git-friendly version control

**Files:**
- `bot.py` - Main bot logic
- `config.py` - Configuration (keep separate)
- `database.py` - Database operations
- `payment.py` - Payment processing
- `fragment.py` - Fragment.com integration
- `utils.py`, `messages.py`, `keyboards.py`, `constants.py` - Supporting modules

## Single File Option

### Option 1: Use Existing Structure (Recommended)
Simply deploy all Python files together. They work as a cohesive unit:

```bash
# Deploy all files
scp *.py your-server:/path/to/bot/
cd /path/to/bot/
python3 bot.py
```

### Option 2: Create Merged File
If you absolutely need a single file, you can create one using:

```bash
python3 << 'EOFPY'
# This script creates main_merged.py with all code combined
# (Implementation would go here)
EOFPY
```

**Note:** A merged file would be ~3800 lines and harder to maintain.

### Option 3: Docker Container
Package everything in a Docker container for easy deployment:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY *.py requirements.txt ./
RUN pip install -r requirements.txt
CMD ["python3", "bot.py"]
```

## Recommendation
Keep the modular structure. It's industry best practice and makes the codebase:
- Easier to understand
- Easier to debug
- Easier to extend
- Easier to test
- Easier to collaborate on

The minor inconvenience of deploying multiple files is outweighed by these benefits.
