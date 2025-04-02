# ustwo IT Tools

A collection of Python tools for IT administration at ustwo, including:
- Google Group management
- Shared Drive administration
- Offboarding automation

## Features

### Google Group Management
- Create new Google Groups with specified settings
- Add and manage members with different permission levels
- Set group visibility and access settings

### Shared Drive Administration
- Create main, external, and GDPR-compliant shared drives
- Add members with customizable roles (Manager, Content Manager, Contributor, etc.)
- Automatically copy folder templates to new drives
- Option to use the same members across multiple drives
- Separate workflows for each drive type (main, external, GDPR)

### Offboarding Automation
- Automate the removal of user access from various systems
- Track offboarding progress and completion

## Requirements

### System Requirements
- **Platform**: macOS with Apple Silicon (M1/M2/M3 series)
- **OS Version**: macOS 11 Big Sur or newer
- **Architecture**: arm64 (bundled app is compiled for Apple Silicon)
- **Disk Space**: ~30MB for the application

### Prerequisite Software
- **GAM Command-line Tool**: Must be installed at `~/bin/gam7/gam` with proper Google API permissions configured
- **JAMF Branding Image**: Expected at `/Library/JAMF/Icon/brandingimage.icns` for UI elements
- **Google Workspace Admin Account**: Required for performing administrative actions

## Setup

### For Development
1. Make sure you have Python 3.x installed
2. Install the required dependencies:
   ```
   pip3 install -r requirements.txt
   ```

### Required Python Packages (for development only)
- PyQt5 >= 5.15.9
- PyQt5-Qt5 >= 5.15.2
- PyQt5-sip >= 12.11.0
- py2app == 0.28.6 (for building)
- setuptools >= 65.5.1
- wheel >= 0.38.4

## Running the Application

You can run the application in three ways:

### Option 1: Using the run script (source code)

```
./run.sh
```

### Option 2: Running the Python script directly

```
python3 ustwo_tools.py
```

### Option 3: Build and run as a macOS application

```
./build_app.sh
```

Then open the generated application in the `dist` folder or copy it to your Applications folder.

## Deployment

### Distributing to Colleagues
The built application is self-contained and includes all Python dependencies. To distribute:

1. Build the application:
   ```
   ./build_app.sh
   ```

2. Copy the resulting `ustwo IT Tools.app` from the `dist` directory to the target machine.

3. Ensure the prerequisites are in place on the target machine:
   - GAM installed at `~/bin/gam7/gam`
   - Proper Google API access for the user's account
   - JAMF branding icon if using UI with branding

4. The application can be placed in the `/Applications` folder or run from any location.

### Notes for IT Administrators
- The app saves configuration in the user's home directory at `~/.shared_drive_tool.json`
- Each module maintains its own state and configuration
- For users with Intel Macs, the app would need to be rebuilt with the `--universal2` flag in PyInstaller

## Project Structure

### Core Application Files
- `ustwo_tools.py` - Main application that provides a tabbed interface
- `Create_Group.py` - Google Groups management tool
- `Shared_Drive.py` - Shared Drive administration tool  
- `Offboarding.py` - User offboarding automation
- `config.py` - Configuration settings for the application
- `assets/` - Contains application assets like icons

### Build System
- `build_app.sh` - Simple script to build the macOS application
- `build_scripts/` - Directory containing all build-related scripts
  - `app_launcher.py` - Entry point for the macOS application
  - `setup_py2app.py` - Configuration for py2app
  - `build_macos_app.sh` - Main build script with detailed options

## Building the macOS App

The build process creates a standalone macOS application that can be distributed to users.

1. Make sure all dependencies are installed:
   ```
   pip3 install -r requirements.txt
   ```

2. Run the build script:
   ```
   ./build_app.sh
   ```

3. The app will be created in the `dist` directory.

## Troubleshooting

### SSH/GitHub Configuration
If you're developing this application, ensure proper SSH configuration for syncing with:
- Gitea repository
- GitHub repositories (personal and company)

The repository supports multiple remote configurations for flexible development workflows.

### ModuleNotFoundError: No module named 'json'

If you encounter the error `ModuleNotFoundError: No module named 'json'` when running the bundled application, this is because the standard library module `json` is not being included in the py2app bundle.

To fix this issue:

1. Ensure that the `setup_py2app.py` file includes 'json' in both the 'packages' and 'includes' lists:
   ```python
   OPTIONS = {
       'argv_emulation': True,
       'iconfile': 'assets/brandingimage.icns',
       'plist': plist,
       'packages': ['PyQt5', 'json'],
       'includes': ['config', 'Create_Group', 'Shared_Drive', 'Offboarding', 'datetime', 'pathlib', 'logging', 'json'],
       # ... other options ...
   }
   ```

2. Rebuild the application using the build script:
   ```
   ./build_app.sh
   ```

### Other Import Errors

If you encounter other import errors with standard library modules, follow the same process by adding them to both the 'packages' and 'includes' lists in `setup_py2app.py`. 