#!/bin/sh
# Finds Python 3 and runs the SessionStart script. Never breaks the session.
dir=${0%/*}
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then
    "$py" "$dir/session_start.py" "$@"
    exit 0
  fi
done
printf '%s\n' '{"systemMessage": "kb-central: install Python 3 to load the central knowledge base index."}'
exit 0
