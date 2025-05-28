# XcodeRemote

A simple command-line tool that triggers Xcode builds via AppleScript and displays the results.

## What it does

1. Sends Cmd+B to Xcode to start a build
2. Waits for the build to finish
3. Parses the build log and shows errors/warnings

## Usage

```bash
# Build a project
./xcode_remote.py /path/to/MyProject.xcodeproj

# Run instead of build
./xcode_remote.py /path/to/MyProject.xcodeproj --action run
```

## Requirements

- macOS with Xcode
- Python 3.6+
- ⚠️ Terminal accessibility permissions (System Settings → Privacy & Security → Accessibility)

## Example Output

```
🔴 ERRORS:
  • /Users/felix/MyProject/Classes/MyView.h:expected ';' after method prototype

🟡 WARNINGS:
  • /Users/felix/MyProject/Utils/Helper.m:unused variable 'temp' [-Wunused-variable]

❌ BUILD FAILED (1 errors)
```

## Disclaimers

⚠️ **This is a quick hack with minimal error handling**  
⚠️ **Your Xcode project must already be open**

That's it. It's just a basic AppleScript wrapper that parses .xcactivitylog files and displays the results in a readable format.