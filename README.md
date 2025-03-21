# ustwo IT Tools

A collection of Python tools for IT administration at ustwo, including:
- Google Group management
- Shared Drive administration
- Offboarding automation

## Setup

1. Make sure you have Python 3.x installed
2. Install the required dependencies:
   ```
   pip3 install -r requirements.txt
   ```

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

## Requirements

See `requirements.txt` for a list of required Python packages.

## Notes

- The application uses PyQt5 for its interface.
- The macOS app is built using py2app.
- The app package includes all dependencies and resources needed to run.

## Troubleshooting

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