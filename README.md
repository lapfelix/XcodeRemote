# XcodeRemote

A command-line tool for remotely triggering Xcode builds via AppleScript with automated error parsing. Perfect for continuous development workflows where you want to trigger builds from your terminal without switching apps.

## Features

- ⚡ **Fast build triggering** - Uses AppleScript to send Cmd+B to Xcode instantly
- 🔄 **Seamless app switching** - Automatically returns to your previous app after triggering build
- 🔍 **Smart error parsing** - Parses compressed .xcactivitylog files for detailed error information  
- 📍 **Precise error locations** - Shows exact file paths and error messages
- 🎯 **Clean output** - Displays only actionable errors and warnings
- ⏱️ **Build monitoring** - Waits for build completion by monitoring DerivedData
- 🚫 **No GUI interruption** - Works without disrupting your current workflow

## Quick Start

```bash
# Make executable
chmod +x xcode_remote.py

# Build a project
./xcode_remote.py /path/to/MyProject.xcodeproj

# Run a project  
./xcode_remote.py /path/to/MyProject.xcodeproj --action run
```

## Usage Examples

```bash
# Basic build
./xcode_remote.py ~/Projects/MyApp/MyApp.xcodeproj

# Run instead of build
./xcode_remote.py ~/Projects/MyApp/MyApp.xcodeproj --action run

# Custom timeout (default: 300 seconds)
./xcode_remote.py ~/Projects/MyApp/MyApp.xcodeproj --timeout 600

# Build specific target
./xcode_remote.py ~/Projects/MyApp/MyApp.xcodeproj --target MyAppTarget
```

## Sample Output

```
Opening project: /Users/felix/Projects/MyApp/MyApp.xcodeproj
Triggering build...
Waiting for build to start...
Build started, waiting for completion...
Build completed

Parsing build log: /Users/felix/Library/Developer/Xcode/DerivedData/MyApp-abc123/Logs/Build/xyz789.xcactivitylog

🔴 ERRORS:
  • /Users/felix/Projects/MyApp/Classes/MyView.h:expected ';' after method prototype
  • /Users/felix/Projects/MyApp/Classes/MyModel.m:use of undeclared identifier 'invalidVar'

🟡 WARNINGS:
  • /Users/felix/Projects/MyApp/Utils/Helper.m:unused variable 'temp' [-Wunused-variable]

❌ BUILD FAILED (2 errors)
```

## Setup Requirements

### System Requirements
- macOS with Xcode installed
- Python 3.6+
- Xcode command line tools

### Permissions Setup
The tool requires accessibility permissions to send keystrokes to Xcode:

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the **+** button and add your terminal app (Terminal, iTerm2, etc.)
3. Enable the toggle for your terminal app

## How It Works

1. **App Detection** - Captures your current app to return to it later
2. **Xcode Activation** - Switches to Xcode and opens the specified project (if not already open)
3. **Build Trigger** - Sends Cmd+B (or Cmd+R) keystroke to trigger build/run
4. **App Return** - Uses Cmd+Tab to immediately return to your previous app
5. **Build Monitoring** - Monitors DerivedData directory for new/updated .xcactivitylog files
6. **Completion Detection** - Waits for log file to stop being modified (build finished)
7. **Error Parsing** - Decompresses and parses the gzipped activity log for errors/warnings
8. **Clean Output** - Displays organized results with file paths and actionable information

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `project_path` | Path to .xcodeproj file | Required |
| `--action` | Action to perform (`build` or `run`) | `build` |
| `--target` | Specific target to build | Uses last selected |
| `--timeout` | Timeout in seconds | `300` |

## Integration Examples

### VS Code Task
Add to `.vscode/tasks.json`:
```json
{
    "label": "Xcode Build",
    "type": "shell",
    "command": "./xcode_remote.py",
    "args": ["${workspaceFolder}/MyApp.xcodeproj"],
    "group": "build"
}
```

### Shell Alias
Add to your `.zshrc` or `.bashrc`:
```bash
alias xbuild="~/path/to/xcode_remote.py"
```

### CI/Development Scripts
```bash
#!/bin/bash
# Quick development build check
if ~/tools/xcode_remote.py ~/Projects/MyApp/MyApp.xcodeproj; then
    echo "✅ Build successful - ready to deploy"
else
    echo "❌ Build failed - check errors above"
    exit 1
fi
```

## Troubleshooting

### Build Not Triggering
- Ensure accessibility permissions are granted to your terminal app
- Check that Xcode is installed and the project path is correct

### Log Parsing Errors
- The tool falls back to reading compressed logs directly if `xcrun xcactivitylog` fails
- Ensure Xcode command line tools are installed: `xcode-select --install`

### App Switching Issues
- Cmd+Tab switching works with macOS's built-in app switching behavior
- If you have custom app switchers, behavior may vary

## Why This Tool?

Traditional Xcode development requires constant app switching to trigger builds. This tool enables:

- **Faster iteration cycles** - Build without leaving your editor
- **Better terminal workflows** - Integrate builds into shell scripts and development tools
- **Reduced context switching** - Stay focused on your code while monitoring build status
- **CI/development pipeline integration** - Programmatically trigger and monitor Xcode builds

Perfect for developers who prefer terminal-based workflows but need to work with Xcode projects.