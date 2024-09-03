# File: ai_response_weaver/weaver.py
#!/usr/bin/env python3
"""
AI Response Weaver

This application monitors a specified file for changes, parses AI-generated code blocks,
and creates or updates corresponding files based on the content.

Usage:
    weaver <file_to_monitor> <log_folder>
"""

import sys
from ai_response_weaver import AIResponseWeaver


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    file_to_monitor = sys.argv[1]
    log_folder = sys.argv[2]

    weaver = AIResponseWeaver(file_to_monitor, log_folder)
    weaver.run()


if __name__ == "__main__":
    main()
