"""
Practical example - Visus Desktop new features

This example demonstrates all the new features:
1. Relative images (anchor + target)
2. Clicking specific coordinates
3. Advanced text typing
4. Expanded keyboard commands
"""

from visus.desktop import VisusBot, execute_tasks


def new_features_example():
    """Demonstrate all the new features of the library."""

    # Initialize the bot
    bot = VisusBot()

    print("Demonstrating NEW FEATURES of Visus Desktop")
    print("=" * 60)

    # 1. RELATIVE IMAGE - find a target near an anchor
    print("\n1. RELATIVE IMAGE")
    print("   Find the 'OK' button near the 'Warning' icon")

    # Individual method
    location = bot.find_relative_image(
        anchor_image='images/warning_icon.png',
        target_image='images/ok_button.png',
        max_distance=150,
        confidence=0.9
    )

    if location:
        print(f"   Target found near the anchor: {location}")
        success = bot.click_relative_image(
            anchor_image='images/warning_icon.png',
            target_image='images/ok_button.png',
            max_distance=150,
            backtrack=True
        )
        print(f"   Click performed: {success}")
    else:
        print("   Target not found near the anchor")

    # 2. CLICK ON SPECIFIC COORDINATES
    print("\n2. CLICK ON COORDINATES")
    print("   Click directly at position (500, 300)")

    success = bot.click_coordinates(
        x=500,
        y=300,
        delay=1,
        mouse_button="left",
        backtrack=True
    )
    print(f"   Click on coordinates performed: {success}")

    # 3. ADVANCED TEXT TYPING
    print("\n3. ADVANCED TYPING")
    print("   Text with special commands")

    success = bot.type_text(
        text="{ctrl}a{del}New text here!{tab}Next field{enter}",
        interval=0.05,
        backtrack=True
    )
    print(f"   Text typed with commands: {success}")

    # 4. KEYBOARD COMMANDS
    print("\n4. KEYBOARD COMMANDS")
    print("   Running the Ctrl+S command (Save)")

    success = bot.keyboard_command(
        command="Ctrl+S",
        delay=1,
        backtrack=True
    )
    print(f"   Ctrl+S command executed: {success}")

    # List all available commands
    commands = bot.get_available_keyboard_commands()
    print(f"   Total available commands: {len(commands)}")
    print(f"   Some examples: {commands[:10]}")

    print("\n" + "=" * 60)
    print("New features demonstration complete!")


def task_list_example():
    """Example using all the new features in a task list."""

    print("\nDemonstrating NEW FEATURES in a Task List")
    print("=" * 60)

    # List with all the new task types
    tasks = [
        # 1. Traditional text search
        {
            'text': 'Login',
            'region': (100, 100, 500, 300),
            'char_type': 'letters',
            'backtrack': True,
            'delay': 1,
            'sendtext': 'admin{tab}password'
        },

        # 2. NEW! Relative image
        {
            'type': 'relative_image',
            'anchor_image': 'images/dialog_header.png',
            'target_image': 'images/close_button.png',
            'max_distance': 200,
            'confidence': 0.9,
            'target_region': (0, 0, 800, 600),
            'specific': True,
            'backtrack': True,
            'delay': 1
        },

        # 3. NEW! Click on coordinates
        {
            'type': 'click',
            'x': 400,
            'y': 250,
            'mouse_button': 'right',
            'delay': 0.5,
            'backtrack': False
        },

        # 4. NEW! Text typing
        {
            'type': 'type_text',
            'text': 'Automation example with Visus Desktop!',
            'interval': 0.03,
            'delay': 1
        },

        # 5. NEW! Keyboard command
        {
            'type': 'keyboard_command',
            'command': 'Ctrl+S',
            'delay': 2
        },

        # 6. Traditional image search
        {
            'image': 'images/confirm_button.png',
            'confidence': 0.9,
            'specific': False,
            'backtrack': True,
            'delay': 1,
            'mouse_button': 'left'
        }
    ]

    # Run all the tasks
    print("Running task list with new features...")
    results = execute_tasks(tasks)

    # Show results
    successful = sum(1 for r in results if r.success)
    print(f"\nExecution complete: {successful}/{len(results)} tasks succeeded")

    for i, result in enumerate(results):
        status = "OK" if result.success else "FAILED"
        print(f"   [{status}] Task {i+1}: {result.task_name}")


def standalone_functions_example():
    """Example using the standalone functions (without instantiating a class)."""

    print("\nDemonstrating STANDALONE FUNCTIONS (new)")
    print("=" * 60)

    from visus.desktop import (
        find_relative_image, click_relative_image,
        click_coordinates, type_text_standalone,
        keyboard_command_standalone, get_available_keyboard_commands
    )

    # 1. Standalone relative image search
    print("\n1. Standalone relative image search")
    location = find_relative_image(
        anchor_image="images/anchor.png",
        target_image="images/target.png",
        max_distance=150
    )
    print(f"   Result: {location}")

    # 2. Standalone relative image click
    print("\n2. Standalone relative image click")
    success = click_relative_image(
        anchor_image="images/anchor.png",
        target_image="images/target.png",
        backtrack=True
    )
    print(f"   Success: {success}")

    # 3. Standalone click on coordinates
    print("\n3. Standalone click on coordinates")
    success = click_coordinates(100, 200, delay=1, backtrack=True)
    print(f"   Success: {success}")

    # 4. Standalone typing
    print("\n4. Standalone typing")
    success = type_text_standalone(
        text="{ctrl}a{del}Standalone text!{enter}",
        backtrack=True
    )
    print(f"   Success: {success}")

    # 5. Standalone keyboard command
    print("\n5. Standalone keyboard command")
    success = keyboard_command_standalone("F5", delay=1, backtrack=True)
    print(f"   Success: {success}")

    # 6. List of commands
    print("\n6. List of available commands")
    commands = get_available_keyboard_commands()
    print(f"   Total: {len(commands)} commands")
    print(f"   First 15: {commands[:15]}")


if __name__ == "__main__":
    try:
        # Demonstrate individual methods
        new_features_example()

        # Demonstrate task lists
        task_list_example()

        # Demonstrate standalone functions
        standalone_functions_example()

        print("\nAll new-feature examples executed!")

    except Exception as e:
        print(f"\nError during execution: {e}")
        print("Tip: make sure the example images exist in the 'images/' folder")
