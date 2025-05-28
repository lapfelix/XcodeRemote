#!/usr/bin/env python3

import argparse
import subprocess
import os
import time
import sys
import glob
import re
import gzip
from pathlib import Path
from typing import Optional, List, Tuple, Dict

class XcodeRemote:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        
        self.project_name = self.project_path.stem
        self.derived_data_path = Path.home() / "Library/Developer/Xcode/DerivedData"
        
    def find_project_derived_data(self) -> Optional[Path]:
        """Find the DerivedData directory for this project"""
        pattern = f"{self.project_name}-*"
        matches = list(self.derived_data_path.glob(pattern))
        if matches:
            return max(matches, key=lambda p: p.stat().st_mtime)
        return None
    
    def get_latest_build_log(self) -> Optional[Path]:
        """Get the most recent build log for the project"""
        derived_data = self.find_project_derived_data()
        if not derived_data:
            return None
            
        logs_dir = derived_data / "Logs" / "Build"
        if not logs_dir.exists():
            return None
            
        log_files = list(logs_dir.glob("*.xcactivitylog"))
        if log_files:
            return max(log_files, key=lambda p: p.stat().st_mtime)
        return None
    
    def open_project_in_xcode(self) -> bool:
        """Open the project in Xcode using AppleScript"""
        applescript = f'''
        tell application "Xcode"
            activate
            open "{self.project_path}"
        end tell
        '''
        
        try:
            subprocess.run(['osascript', '-e', applescript], check=True)
            time.sleep(2)  # Give Xcode time to open
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error opening project in Xcode: {e}")
            return False
    
    def trigger_build(self, action: str = "build", target: Optional[str] = None) -> bool:
        """Trigger a build action in Xcode using AppleScript"""
        if action == "build":
            keystroke_cmd = "b"
        elif action == "run":
            keystroke_cmd = "r"
        else:
            print(f"Unknown action: {action}")
            return False
        
        # Simple approach: activate Xcode, trigger build, then Cmd+Tab back
        applescript = f'''
        tell application "Xcode"
            activate
        end tell
        
        delay 0.1
        
        tell application "System Events"
            keystroke "{keystroke_cmd}" using {{command down}}
        end tell
        
        delay 0.1
        
        tell application "System Events"
            keystroke tab using {{command down}}
        end tell
        '''
        
        try:
            subprocess.run(['osascript', '-e', applescript], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error triggering {action}: {e}")
            print("Note: You may need to grant Terminal accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility")
            return False
    
    def wait_for_build_completion(self, timeout: int = 300) -> Tuple[bool, bool]:
        """Wait for build completion by monitoring DerivedData. Returns (completed, success)"""
        initial_log = self.get_latest_build_log()
        initial_time = time.time()
        
        print("Waiting for build to start...")
        
        # Wait for a new log file to appear or existing one to be modified
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_log = self.get_latest_build_log()
            
            if current_log and (not initial_log or current_log != initial_log or 
                               current_log.stat().st_mtime > initial_time):
                print("Build started, waiting for completion...")
                break
            
            time.sleep(1)
        else:
            print("Timeout waiting for build to start")
            return False, False
        
        # Now wait for the build to finish (log file stops being modified)
        last_modified = 0
        stable_count = 0
        
        while time.time() - start_time < timeout:
            current_log = self.get_latest_build_log()
            if current_log:
                current_modified = current_log.stat().st_mtime
                if current_modified == last_modified:
                    stable_count += 1
                    if stable_count >= 3:  # File hasn't changed for 3 seconds
                        print("Build completed")
                        # Check if build was successful by parsing the log
                        results = self.parse_build_log(current_log)
                        build_success = len(results["errors"]) == 0
                        return True, build_success
                else:
                    last_modified = current_modified
                    stable_count = 0
            
            time.sleep(1)
        
        print("Timeout waiting for build completion")
        return False, False
    
    def parse_build_log(self, log_path: Path) -> Dict[str, List[str]]:
        """Parse the xcactivitylog file for errors and warnings"""
        result = {"errors": set(), "warnings": set(), "notes": set()}
        
        # Read the gzipped log file directly (xcrun xcactivitylog often fails)
        try:
            with gzip.open(log_path, 'rt', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Look for error patterns in raw content
                lines = content.split('\n')
                for line in lines:
                    # Standard error format with explicit "error:"
                    if 'error:' in line.lower():
                        file_error_match = re.search(r'(/[^:]+\.(?:swift|c(?:pp)?|h|mm?)):\d+:\d+.*?error:\s*(.+)', line, re.IGNORECASE)
                        if file_error_match:
                            error_msg = f"{file_error_match.group(1)}:{file_error_match.group(2).strip()}"
                            result["errors"].add(error_msg)
                        else:
                            # Handle simple error format for Swift and ObjC files: /path/file.ext:error message
                            simple_error_match = re.search(r'(/[^:]+\.(?:swift|c(?:pp)?|h|mm?)):(.+)', line, re.IGNORECASE)
                            if simple_error_match:
                                file_path = simple_error_match.group(1)
                                message_part = simple_error_match.group(2)
                                # Clean up the message - extract just the error after the last file path
                                # Look for the actual error message pattern
                                error_msg_match = re.search(r'.*'+re.escape(file_path)+r':(.+?)(?:\s*$)', message_part)
                                if error_msg_match:
                                    clean_message = error_msg_match.group(1).strip()
                                else:
                                    # Fallback: just take everything after the colon, clean up quotes
                                    clean_message = message_part.strip()
                                    clean_message = re.sub(r'.*"([^"]+)".*', r'\1', clean_message)
                                    if '"' not in clean_message:  # If no quotes found, keep original
                                        clean_message = message_part.strip()
                                if clean_message:
                                    result["errors"].add(f"{file_path}:{clean_message}")
                    
                    # Swift compilation errors that don't use "error:" prefix (but limit processing)
                    elif len(line) < 1000 and re.search(r'(/[^:]+\.swift):\d+:\d+\s+', line):
                        # Check if this looks like a Swift error (common patterns)
                        if any(pattern in line.lower() for pattern in [
                            'cannot override', 'ambiguous use', 'overriding declaration', 'overriding property must be',
                            'conflicts with', 'must be unwrapped', 'requires an \'override\' keyword',
                            'getter for', 'setter for', 'value of optional type'
                        ]):
                            swift_match = re.search(r'(/[^:]+\.swift):(\d+):(\d+)\s+(.+)', line)
                            if swift_match:
                                file_path, line_num, col_num, message = swift_match.groups()
                                clean_message = message.strip()[:200]  # Limit message length
                                result["errors"].add(f"{file_path}:{line_num}:{col_num} {clean_message}")
                    
                    # Objective-C errors (but limit processing)
                    elif len(line) < 1000 and re.search(r'(/[^:]+\.mm?):\d+:\d+\s+', line):
                        if any(pattern in line.lower() for pattern in [
                            'property', 'not found', 'no visible @interface', 'declares the selector'
                        ]):
                            objc_match = re.search(r'(/[^:]+\.mm?):(\d+):(\d+)\s+(.+)', line)
                            if objc_match:
                                file_path, line_num, col_num, message = objc_match.groups()
                                clean_message = message.strip()[:200]  # Limit message length
                                result["errors"].add(f"{file_path}:{line_num}:{col_num} {clean_message}")
                    
                    # Warning format
                    elif 'warning:' in line.lower():
                        file_warning_match = re.search(r'(/[^:]+\.(?:swift|c(?:pp)?|h|mm?)):\d+:\d+.*?warning:\s*(.+)', line, re.IGNORECASE)
                        if file_warning_match:
                            warning_msg = f"{file_warning_match.group(1)}:{file_warning_match.group(2).strip()}"
                            result["warnings"].add(warning_msg)
                    
                    # Note format
                    elif 'note:' in line.lower():
                        note_match = re.search(r'note:\s*(.+)', line, re.IGNORECASE)
                        if note_match:
                            result["notes"].add(note_match.group(1).strip())
        except Exception as read_error:
            print(f"Failed to read log file: {read_error}")
        
        # Convert sets back to lists for consistency
        return {
            "errors": list(result["errors"]),
            "warnings": list(result["warnings"]),
            "notes": list(result["notes"])
        }
    
    def build(self, action: str = "build", target: Optional[str] = None, timeout: int = 300) -> bool:
        """Execute the complete build workflow"""
        # Check if Xcode is already active
        get_current_app = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            return frontApp
        end tell
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', get_current_app], capture_output=True, text=True, check=True)
            current_app = result.stdout.strip()
            xcode_already_active = (current_app == "Xcode")
        except:
            xcode_already_active = False
        
        if not xcode_already_active:
            print(f"Opening project: {self.project_path}")
            if not self.open_project_in_xcode():
                return False
        
        print(f"Triggering {action}...")
        if not self.trigger_build(action, target):
            return False
        
        completed, build_success = self.wait_for_build_completion(timeout)
        if not completed:
            return False
        
        # Parse the results from the build log
        log_path = self.get_latest_build_log()
        if log_path:
            print(f"\nParsing build log: {log_path}")
            results = self.parse_build_log(log_path)
            
            if results["errors"]:
                print("\n🔴 ERRORS:")
                for error in results["errors"]:
                    print(f"  • {error}")
            
            if results["warnings"]:
                print("\n🟡 WARNINGS:")
                for warning in results["warnings"]:
                    print(f"  • {warning}")
            
            
            if results["errors"]:
                print(f"\n❌ BUILD FAILED ({len(results['errors'])} errors)")
                return False
            elif results["warnings"]:
                print(f"\n⚠️  BUILD COMPLETED WITH WARNINGS ({len(results['warnings'])} warnings)")
                return True
            else:
                print("\n✅ BUILD SUCCESSFUL")
                return True
        else:
            print("No build log found")
            return build_success

def check_accessibility_permissions():
    """Check if accessibility permissions are granted"""
    test_script = '''
    tell application "System Events"
        return true
    end tell
    '''
    
    try:
        subprocess.run(['osascript', '-e', test_script], 
                      capture_output=True, text=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def main():
    parser = argparse.ArgumentParser(description="Remote Xcode build tool")
    parser.add_argument("project_path", help="Path to the .xcodeproj file")
    parser.add_argument("--action", choices=["build", "run"], default="build", 
                       help="Action to perform (default: build)")
    parser.add_argument("--target", help="Specific target to build (optional)")
    parser.add_argument("--timeout", type=int, default=300, 
                       help="Timeout in seconds (default: 300)")
    
    args = parser.parse_args()
    
    # Check accessibility permissions
    if not check_accessibility_permissions():
        print("⚠️  Accessibility permissions required!")
        print("Go to: System Settings → Privacy & Security → Accessibility")
        print("Add your terminal app and enable it.")
        sys.exit(1)
    
    try:
        xcode_remote = XcodeRemote(args.project_path)
        success = xcode_remote.build(args.action, args.target, args.timeout)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()