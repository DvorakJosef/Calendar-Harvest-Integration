#!/usr/bin/env python3
"""
Script to create a clean Calendar Harvest Integration project
separated from the Finhealth project
"""

import os
import shutil
import sys
from pathlib import Path

def create_clean_calendar_harvest_project():
    """Create a clean Calendar Harvest Integration project"""
    
    # Define source and destination paths
    source_dir = Path("/Users/josefdvorak/Documents/augment-projects/TS Auto/calendar-harvest-integration")
    dest_dir = Path("/Users/josefdvorak/Documents/augment-projects/Calendar-Harvest-Integration-Clean")
    
    print(f"🧹 Creating clean Calendar Harvest Integration project")
    print(f"Source: {source_dir}")
    print(f"Destination: {dest_dir}")
    
    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created directory: {dest_dir}")
    
    # Define Calendar Harvest Integration files to copy
    calendar_harvest_files = [
        # Core Python files
        "main.py",
        "models.py", 
        "auth.py",
        "google_calendar_service.py",
        "harvest_service.py",
        "mapping_engine.py",
        "bulk_mapping.py",
        "pattern_recognition.py",
        "setup_wizard.py",
        "config.py",
        "create_db.py",
        "init_db.py",
        "migrate_to_multiuser.py",
        
        # Configuration files
        "requirements.txt",
        ".env.example",
        "README.md",
        "run.py",
        "setup.py",
        
        # Test and debug files
        "test_harvest.py",
        "debug_harvest.py", 
        "debug_harvest_detailed.py",
        "test_time_entry.py",
        
        # Database files
        "calendar_harvest.db",
        
        # Deployment files
        "app.yaml",
        ".gcloudignore",
        "Dockerfile",
        "deploy.sh",
        "setup-production.sh",
        "switch-env.sh",
        
        # Documentation
        "DEPLOYMENT_GUIDE.md",
        "MULTIUSER_SETUP.md",
        "OAUTH_SETUP.md",
        "ONBOARDING_GUIDE_CZ.md",
        "CLEANUP_NOTES.md",
        "cloud-sql-config.txt",
        "create_tables.sql",
        "health_check.py",
        "init_production_db.py",
    ]
    
    # Copy individual files
    copied_files = []
    for file_name in calendar_harvest_files:
        source_file = source_dir / file_name
        dest_file = dest_dir / file_name
        
        if source_file.exists():
            try:
                shutil.copy2(source_file, dest_file)
                copied_files.append(file_name)
                print(f"✅ Copied: {file_name}")
            except Exception as e:
                print(f"❌ Failed to copy {file_name}: {e}")
        else:
            print(f"⚠️  Not found: {file_name}")
    
    # Copy directories
    directories_to_copy = [
        "templates",
        "static", 
        "instance"
    ]
    
    for dir_name in directories_to_copy:
        source_dir_path = source_dir / dir_name
        dest_dir_path = dest_dir / dir_name
        
        if source_dir_path.exists():
            try:
                if dest_dir_path.exists():
                    shutil.rmtree(dest_dir_path)
                shutil.copytree(source_dir_path, dest_dir_path)
                print(f"✅ Copied directory: {dir_name}")
            except Exception as e:
                print(f"❌ Failed to copy directory {dir_name}: {e}")
        else:
            print(f"⚠️  Directory not found: {dir_name}")
    
    # Create environment files
    env_files = [".env.development", ".env.production"]
    for env_file in env_files:
        source_env = source_dir / env_file
        dest_env = dest_dir / env_file
        
        if source_env.exists():
            try:
                shutil.copy2(source_env, dest_env)
                print(f"✅ Copied: {env_file}")
            except Exception as e:
                print(f"❌ Failed to copy {env_file}: {e}")
    
    # Create a clean README
    readme_content = """# Calendar-Harvest Integration (Clean)

A standalone Calendar-Harvest Integration application that automatically syncs Google Calendar events to Harvest timesheets.

## 🎯 Features

- **Multi-user support** with Google Workspace authentication
- **Smart event grouping** - Combines events by project, task, and date  
- **Pattern recognition** - Automatically suggests mappings
- **Real-time preview** - See exactly what entries will be created
- **Duplicate detection** - Prevents duplicate time entries

## 🚀 Quick Start

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Run locally
python3 main.py
# Access at: http://127.0.0.1:5001
```

### Production
```bash
# Setup production infrastructure
./setup-production.sh

# Deploy to Google Cloud
./deploy.sh
```

## 📁 Clean Project Structure

This is a clean, standalone version of the Calendar-Harvest Integration, completely separated from any other projects for clarity and maintainability.

## 🔧 Environment Management

- **Development**: SQLite database, localhost OAuth
- **Production**: PostgreSQL on Google Cloud SQL, europe-central2

## 📊 Key Features

### Smart Grouping
Events are automatically grouped by project, task, and date to create cleaner timesheets.

### Multi-user Support  
- Google Workspace authentication
- Per-user configurations
- Isolated data and mappings

---

**Note**: This is a clean, standalone project separated from Finhealth and other applications.
"""
    
    readme_path = dest_dir / "README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"✅ Created clean README.md")
    
    # Create a .gitignore file
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment variables
.env
.env.local
.env.development.local
.env.production.local

# Database
*.db
*.sqlite3
instance/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Google Cloud
.gcloudignore
cloud-sql-config.txt

# Logs
*.log
logs/

# Temporary files
temp/
tmp/
"""
    
    gitignore_path = dest_dir / ".gitignore"
    with open(gitignore_path, 'w') as f:
        f.write(gitignore_content)
    print(f"✅ Created .gitignore")
    
    print(f"\n🎉 Clean Calendar Harvest Integration project created!")
    print(f"📁 Location: {dest_dir}")
    print(f"📊 Files copied: {len(copied_files)}")
    print(f"📂 Directories copied: {len(directories_to_copy)}")
    
    print(f"\n🚀 Next steps:")
    print(f"1. cd {dest_dir}")
    print(f"2. cp .env.example .env")
    print(f"3. Edit .env with your credentials")
    print(f"4. python3 main.py")
    
    return True

if __name__ == "__main__":
    try:
        success = create_clean_calendar_harvest_project()
        if success:
            print("\n✅ Project separation completed successfully!")
        else:
            print("\n❌ Project separation failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
