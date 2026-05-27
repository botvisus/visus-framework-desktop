"""
Basic example: Using visus-desktop for simple automation tasks.

This example demonstrates:
1. Basic package usage
2. Simple task execution
3. Finding and clicking text elements
"""

from visus.desktop import VisusBot, execute_tasks, find_text, click_text
from visus.desktop import BotVisionConfig


def main():
    print("Visus Desktop - Basic Example")
    print("=" * 40)

    # Example 1: Using convenience functions
    print("\n1. Using convenience functions:")

    # Find text on screen
    print("Looking for 'Start' button...")
    if find_text("Start"):
        print("Found 'Start' button!")
    else:
        print("'Start' button not found")

    # Click a button
    print("Trying to click 'OK' button...")
    if click_text("OK"):
        print("Successfully clicked 'OK' button!")
    else:
        print("Could not click 'OK' button")

    # Example 2: Using task configuration
    print("\n2. Using task-based approach:")

    # Define tasks. Each task is a dictionary describing a single action
    # (text/image search, click, type, etc.).
    tasks = [
        {
            "text": "Login",
            "region": (0, 0, 500, 300),  # x, y, width, height
        },
        {
            "text": "Username",
            "region": (0, 0, 500, 300),
        },
        {
            "text": "Submit",
            "region": (100, 200, 400, 400),
        },
    ]

    # Execute tasks
    results = execute_tasks(tasks)

    # Display results. execute_tasks returns a list of TaskResult objects.
    for result in results:
        status = "PASSED" if result.success else "FAILED"
        print(f"Task '{result.task_name}': {status}")

        if not result.success and result.error:
            print(f"  Error: {result.error}")

    # Example 3: Using the VisusBot class with custom configuration
    print("\n3. Using VisusBot class with custom config:")

    # Create custom configuration. BotVisionConfig takes a single dict.
    config = BotVisionConfig({
        "confidence_threshold": 90.0,  # Higher confidence requirement
        "retry_attempts": 5,           # More retries
        "log_level": "DEBUG",          # Verbose logging
    })

    # Create VisusBot instance
    bot = VisusBot(config=config)

    # Define a simple task
    simple_task = {
        "text": "Desktop",
        "region": None,  # Search entire screen
    }

    # Execute task
    results = bot.execute_tasks([simple_task])

    for result in results:
        print(f"Demo task result: success={result.success}, "
              f"location={result.location}")


if __name__ == "__main__":
    main()
