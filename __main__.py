#!/usr/bin/env python3
"""
OpenClaw Skill Entry Point for Claw Conductor

This file is invoked by OpenClaw when the skill is triggered via Discord binding.
"""

import sys
import os
import json
import traceback

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from orchestrator import Orchestrator


def main():
    """Main entry point for skill invocation"""
    try:
        # Parse input from OpenClaw (via stdin or command line args)
        if len(sys.argv) > 1:
            # Command line argument mode
            user_message = ' '.join(sys.argv[1:])
        else:
            # Stdin mode (JSON payload from OpenClaw)
            input_data = sys.stdin.read()
            try:
                payload = json.loads(input_data)
                user_message = payload.get('message', '')
                channel_id = payload.get('channel_id')
                channel_name = payload.get('channel_name')
            except json.JSONDecodeError:
                # Fallback: treat stdin as plain text message
                user_message = input_data.strip()
                channel_id = None
                channel_name = None

        if not user_message:
            print("Error: No message provided", file=sys.stderr)
            sys.exit(1)

        # Initialize orchestrator
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'agent-registry.json')
        orchestrator = Orchestrator(config_path)

        # Handle the message with triage
        result = orchestrator.handle_message(
            request=user_message,
            channel_id=channel_id if 'channel_id' in locals() else None,
            channel_name=channel_name if 'channel_name' in locals() else None
        )

        # Output result
        if result.get('success'):
            print(result.get('response', 'Task completed successfully'))
        else:
            error_msg = result.get('error', 'Unknown error occurred')
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        # Log full traceback for debugging
        error_trace = traceback.format_exc()
        error_log = f"/tmp/claw-conductor-error.log"

        with open(error_log, 'a') as f:
            f.write(f"\n\n=== Error at {os.popen('date').read().strip()} ===\n")
            f.write(error_trace)

        print(f"Error: {str(e)}", file=sys.stderr)
        print(f"Full traceback logged to: {error_log}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
