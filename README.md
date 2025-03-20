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

1. Clone the repository:
```bash
git clone ssh://git@10.0.4.2:2221/daryl/ustwo-it-tools.git
cd ustwo-it-tools
```

2. Install required Python packages:
```bash
pip install PyQt5
```

3. Ensure GAM is installed and configured:
```bash
# GAM should be installed at ~/bin/gam7/gam
# If installed elsewhere, set the GAM_PATH environment variable
export GAM_PATH=/path/to/your/gam
```

## Directory Structure

```
ustwo_it_tools/
├── assets/              # Shared assets
│   └── brandingimage.icns
├── config/             # Configuration files
│   └── .gitkeep
├── ustwo_tools.py      # Main unified application
├── config.py           # Shared configuration module
├── Create_Group.py     # Google Groups tool
├── Shared_Drive.py     # Shared Drive tool
└── Offboarding.py      # Offboarding tool
```

## Usage

Run the unified application:
```bash
python ustwo_tools.py
```

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is proprietary and confidential. All rights reserved. 