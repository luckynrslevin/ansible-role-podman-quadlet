#!/usr/bin/env python3
"""
Patch structured config files (YAML or JSON) with dot-notation key-value pairs.

Usage:
  patch_structured_config.py --file PATH --format {yaml|json} --patches 'JSON_STRING'

The --patches argument is a JSON object where keys use dot-notation for nested
access (e.g. "server.port" sets data["server"]["port"]).

Outputs a JSON result: {"changed": true/false, "msg": "..."}
Exit codes: 0 = success, 1 = error
"""

import argparse
import copy
import json
import os
import sys


def set_nested(data, dotted_key, value):
    """Set a value in a nested dict using dot-notation key."""
    keys = dotted_key.split('.')
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def load_yaml(path):
    """Load a YAML file."""
    try:
        import yaml
    except ImportError:
        print(json.dumps({"changed": False, "msg": "PyYAML is not installed"}))
        sys.exit(1)
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    return data


def save_yaml(path, data):
    """Save data as YAML."""
    import yaml
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_json(path):
    """Load a JSON file."""
    with open(path, 'r') as f:
        data = json.load(f)
    if data is None:
        data = {}
    return data


def save_json(path, data):
    """Save data as JSON."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description='Patch structured config files')
    parser.add_argument('--file', required=True, help='Path to the config file')
    parser.add_argument('--format', required=True, choices=['yaml', 'json'],
                        help='File format')
    parser.add_argument('--patches',
                        help='JSON string of key-value patches (dot-notation keys)')
    parser.add_argument('--patches-file',
                        help='Path to JSON file containing key-value patches')
    parser.add_argument('--key',
                        help='Single key to patch (dot-notation)')
    parser.add_argument('--value',
                        help='Value for the single key (auto-detects type)')
    args = parser.parse_args()

    file_path = args.file
    file_format = args.format

    # Parse patches from various input methods
    if args.key is not None:
        # Single key-value mode
        value = args.value
        # Try to parse value as JSON for proper typing (int, bool, list, etc.)
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            pass  # Keep as string
        patches = {args.key: value}
    elif args.patches_file:
        try:
            with open(args.patches_file, 'r') as f:
                patches = json.load(f)
        except (ValueError, TypeError, IOError) as e:
            print(json.dumps({"changed": False,
                              "msg": "Invalid patches file: %s" % str(e)}))
            sys.exit(1)
    elif args.patches:
        try:
            patches = json.loads(args.patches)
        except (ValueError, TypeError) as e:
            print(json.dumps({"changed": False,
                              "msg": "Invalid patches JSON: %s" % str(e)}))
            sys.exit(1)
    else:
        print(json.dumps({"changed": False,
                          "msg": "Provide --patches, --patches-file, or --key/--value"}))
        sys.exit(1)

    if not isinstance(patches, dict):
        print(json.dumps({"changed": False, "msg": "Patches must be a JSON object"}))
        sys.exit(1)

    # Check file exists
    if not os.path.isfile(file_path):
        print(json.dumps({"changed": False,
                          "msg": "File does not exist: %s" % file_path}))
        sys.exit(1)

    # Load existing data
    try:
        if file_format == 'yaml':
            data = load_yaml(file_path)
        else:
            data = load_json(file_path)
    except Exception as e:
        print(json.dumps({"changed": False,
                          "msg": "Failed to read %s: %s" % (file_path, str(e))}))
        sys.exit(1)

    # Deep copy to compare later
    original = copy.deepcopy(data)

    # Apply patches
    for key, value in patches.items():
        set_nested(data, key, value)

    # Check if anything changed
    if data == original:
        print(json.dumps({"changed": False, "msg": "No changes needed"}))
        sys.exit(0)

    # Write back
    try:
        if file_format == 'yaml':
            save_yaml(file_path, data)
        else:
            save_json(file_path, data)
    except Exception as e:
        print(json.dumps({"changed": False,
                          "msg": "Failed to write %s: %s" % (file_path, str(e))}))
        sys.exit(1)

    print(json.dumps({"changed": True, "msg": "Config patched successfully"}))
    sys.exit(0)


if __name__ == '__main__':
    main()
