"""
Visus Desktop usage example - demonstrates backward compatibility with the
original code.

This example shows how to use the visus-desktop package in the same way as the
original bot_vision.py script.
"""

# MODE 1: Use exactly like the original code (full backward compatibility)
from visus.desktop import click_images, run_automation

# Example of simple tasks
simple_tasks = [
    {
        'text': 'Login',
        'region': (100, 100, 500, 300),
        'char_type': 'both',
        'delay': 1
    },
    {
        'image': 'confirm_button.png',
        'region': (200, 400, 300, 100),
        'confidence': 0.8,
        'delay': 2
    }
]

# Example of multiple task lists (as in the original)
multiple_task_lists = [
    [  # List 1
        {'text': 'First', 'region': (0, 0, 800, 600)},
        {'text': 'Second', 'region': (0, 0, 800, 600)}
    ],
    [  # List 2
        {'image': 'third.png', 'region': (100, 100, 200, 200)},
        {'text': 'Fourth', 'region': (0, 0, 800, 600), 'sendtext': '{ctrl}a{del}New text{enter}'}
    ]
]

# MODE 2: Use the standalone functions (compatibility with original functions)
from visus.desktop import (
    limpar_texto,
    matches_filter,
    show_overlay,
    preprocess_image_for_ocr,
    locate_image_with_retry,
    find_text_with_multiple_preprocessing
)

# MODE 3: Object-oriented usage (new API)
from visus.desktop import VisusBot

# MODE 4: Convenience functions
from visus.desktop import execute_tasks, find_text, click_text, find_image, click_image


def original_usage_example():
    """Example using exactly the same approach as the original code."""
    print("=== Example of usage identical to the original code ===")

    # For a simple list
    print("Running a simple list...")
    click_images(simple_tasks)

    # For multiple lists (exactly like the original)
    print("Running multiple lists...")
    run_automation(multiple_task_lists)


def standalone_functions_example():
    """Example using standalone functions."""
    print("=== Standalone functions example ===")

    # Text cleaning (exactly like the original). filter_type "numbers" keeps
    # only digits.
    clean = limpar_texto("  123abc!@#  ", "numbers")
    print(f"Cleaned text: '{clean}'")

    # Filter check
    is_valid = matches_filter("123", "numbers")
    print(f"'123' is valid for numbers: {is_valid}")

    # Locate an image (without instantiating any class)
    # location = locate_image_with_retry("my_image.png", confidence=0.9)


def object_oriented_example():
    """Example using the new object-oriented API."""
    print("=== New object-oriented API example ===")

    # Create the bot instance
    bot = VisusBot()

    # Run tasks
    results = bot.execute_tasks(simple_tasks)

    # Use individual methods
    location = bot.find_text("Login", region=(100, 100, 500, 300))
    if location:
        print(f"Text found at: {location}")

    # Click on text
    success = bot.click_text("Confirm", region=(200, 200, 600, 400))
    print(f"Click performed: {success}")


def convenience_example():
    """Example using the convenience functions."""
    print("=== Convenience functions example ===")

    # Direct execution
    results = execute_tasks(simple_tasks)

    # Text search
    location = find_text("Login", region=(100, 100, 500, 300))

    # Click on text
    success = click_text("Confirm", region=(200, 200, 600, 400))


if __name__ == "__main__":
    print("Visus Desktop - Usage Examples")
    print("=" * 50)

    # Demonstrate all usage modes
    original_usage_example()
    standalone_functions_example()
    object_oriented_example()
    convenience_example()

    print("\nThe visus-desktop package is fully backward compatible with the original code!")
    print("All functionality from bot_vision.py has been successfully ported!")
