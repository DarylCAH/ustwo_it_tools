# ustwo IT Tools

A unified Python application for managing Google Workspace resources at ustwo, combining three powerful tools into a single interface:

1. Google Groups Management
2. Shared Drive Creation and Management
3. User Offboarding

## Features

### Google Groups Tool
- Create new Google Groups with custom permissions
- Add members with different roles (owners, managers, members)
- Configure access settings via a visual permission matrix
- Persistent email storage for convenience
- Custom branded dialogs for all user interactions

### Shared Drive Tool
- Create new Google Shared Drives
- Optional 2-folder template copy (Internal/External/GDPR)
- Bulk membership management
- Support for external and GDPR-compliant drives
- Custom branded dialogs for all user interactions

### Offboarding Tool
- Process multiple users simultaneously
- Transfer owned groups
- Remove users from all groups
- Set out of office messages
- Reset passwords
- Sign out from all devices
- Hide from directory
- Move to Leavers OU

## Requirements

- Python 3.x
- PyQt5
- GAM (Google Apps Manager) installed at `~/bin/gam7/gam`
- macOS (for branding icon support)

## Installation

### Option 1: Run as Python Script

1. Clone the repository:
```bash
git clone ssh://git@10.0.4.2:2221/daryl/ustwo-it-tools.git
cd ustwo-it-tools
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Ensure GAM is installed and configured:
```bash
# GAM should be installed at ~/bin/gam7/gam
# If installed elsewhere, set the GAM_PATH environment variable
export GAM_PATH=/path/to/your/gam
```

### Option 2: Build macOS App

1. Clone the repository and navigate to it:
```bash
git clone ssh://git@10.0.4.2:2221/daryl/ustwo-it-tools.git
cd ustwo-it-tools
```

2. Run the build script:
```bash
./build_app.sh
```

3. The app will be created in the `dist/` directory. You can then:
   - Double-click to run it
   - Drag it to your Applications folder
   - Create an alias on your desktop

## Directory Structure

```
ustwo_it_tools/
├── assets/              # Shared assets
│   └── brandingimage.icns
├── config/             # Configuration files
│   └── .gitkeep
├── build_app.sh        # macOS app build script
├── requirements.txt    # Python dependencies
├── setup.py           # py2app configuration
├── ustwo_tools.py     # Main unified application
├── config.py          # Shared configuration module
├── Create_Group.py    # Google Groups tool
├── Shared_Drive.py    # Shared Drive tool
└── Offboarding.py     # Offboarding tool
```

## Usage

### Running as Python Script
```bash
python ustwo_tools.py
```

### Running as macOS App
1. Double-click the app in the `dist/` directory
2. Or drag it to your Applications folder and launch it from there

The application provides a tabbed interface to access all three tools. Each tool maintains its own configuration and settings.

## Configuration

The application uses a shared configuration module (`config.py`) that manages:
- Path to GAM binary
- Asset locations
- Configuration file storage
- Settings persistence

Configuration files are stored in the `config/` directory and are automatically created when needed.

## Development

The application is structured to allow each tool to run independently or as part of the unified interface. Each tool can be run separately:

```bash
# Run individual tools
python Create_Group.py
python Shared_Drive.py
python Offboarding.py
```

## Building the macOS App

To build the macOS app:

1. Make sure you have all requirements installed:
```bash
pip install -r requirements.txt
```

2. Run the build script:
```bash
./build_app.sh
```

3. The app will be created in the `dist/` directory.

To rebuild the app after changes:
```bash
# Clean previous builds
rm -rf build dist

# Rebuild
./build_app.sh
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is proprietary and confidential. All rights reserved. 