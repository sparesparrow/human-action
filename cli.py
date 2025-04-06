#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command-line interface for audio book generation pipeline
"""

import argparse
import sys

from pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description="Audio Book Generation Pipeline")

    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Pipeline commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the pipeline")
    run_parser.add_argument("--start", help="Start from this stage")
    run_parser.add_argument("--end", help="End at this stage")
    run_parser.add_argument(
        "--force", action="store_true", help="Force rerun of completed stages"
    )
    run_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset pipeline state")
    reset_parser.add_argument(
        "--stages", nargs="*", help="Stages to reset (default: all)"
    )
    reset_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show pipeline status")
    status_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--audio", action="store_true", help="Test audio files")
    test_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = Pipeline(args.config)

    # Execute commands
    if args.command == "run":
        success = pipeline.run_pipeline(args.start, args.end, force=args.force)
        sys.exit(0 if success else 1)

    elif args.command == "reset":
        pipeline.reset_state(args.stages)
        print("Pipeline state reset.")

    elif args.command == "status":
        # Display pipeline status
        state = pipeline.state
        print("\nAudio Book Generation Pipeline Status:")
        print("-" * 50)

        for stage, status in state["stages"].items():
            completed = "✅" if status["completed"] else "❌"
            files_count = len(status["files_processed"])
            print(f"{stage.ljust(25)} {completed} ({files_count} files processed)")

        print("-" * 50)
        if state["last_run"]:
            print(f"Last run: {state['last_run']}")

    elif args.command == "test":
        if args.audio:
            from test_audio_paths import check_audio_references, create_test_html

            check_audio_references()
            create_test_html()
            print("Audio tests completed.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-

"""
Command-line interface for audio book generation pipeline
"""

import argparse
import sys

from pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description="Audio Book Generation Pipeline")

    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Pipeline commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the pipeline")
    run_parser.add_argument("--start", help="Start from this stage")
    run_parser.add_argument("--end", help="End at this stage")
    run_parser.add_argument(
        "--force", action="store_true", help="Force rerun of completed stages"
    )
    run_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset pipeline state")
    reset_parser.add_argument(
        "--stages", nargs="*", help="Stages to reset (default: all)"
    )
    reset_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show pipeline status")
    status_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--audio", action="store_true", help="Test audio files")
    test_parser.add_argument(
        "--config", default="config.yaml", help="Configuration file"
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = Pipeline(args.config)

    # Execute commands
    if args.command == "run":
        success = pipeline.run_pipeline(args.start, args.end, force=args.force)
        sys.exit(0 if success else 1)

    elif args.command == "reset":
        pipeline.reset_state(args.stages)
        print("Pipeline state reset.")

    elif args.command == "status":
        # Display pipeline status
        state = pipeline.state
        print("\nAudio Book Generation Pipeline Status:")
        print("-" * 50)

        for stage, status in state["stages"].items():
            completed = "✅" if status["completed"] else "❌"
            files_count = len(status["files_processed"])
            print(f"{stage.ljust(25)} {completed} ({files_count} files processed)")

        print("-" * 50)
        if state["last_run"]:
            print(f"Last run: {state['last_run']}")

    elif args.command == "test":
        if args.audio:
            from test_audio_paths import check_audio_references, create_test_html

            check_audio_references()
            create_test_html()
            print("Audio tests completed.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
