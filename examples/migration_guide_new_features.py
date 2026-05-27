"""
Migration guide - Visus Desktop
New features

This file shows how to migrate from the old code to the new features available
in the visus-desktop library.

The old package was installed with `pip install bot-vision-suite` and imported
as `from bot_vision import BotVision`. The new package is installed with
`pip install visus-desktop` and imported as `from visus.desktop import VisusBot`.
"""


# BEFORE - Legacy style (original bot_vision.py)
def legacy_code_example():
    """Example of how things were done before the new features.

    In the legacy package this used `from bot_vision import click_images`.
    With visus-desktop the same function is available and fully compatible.
    """

    from visus.desktop import click_images

    # Tasks limited to the basic types
    legacy_tasks = [
        {
            'text': 'Login',
            'region': (100, 100, 500, 300),
            'char_type': 'letters',
            'delay': 1
        },
        {
            'image': 'button.png',
            'confidence': 0.9,
            'delay': 2
        }
    ]

    # Only these basic types used to be supported
    click_images(legacy_tasks)


# AFTER - New code with ALL the features
def new_code_example():
    """Example using ALL the new features."""

    from visus.desktop import VisusBot, execute_tasks

    # Bot with all the features
    bot = VisusBot()

    # ===== NEW FEATURE 1: RELATIVE IMAGE =====
    print("1. RELATIVE IMAGE - find a target near an anchor")

    # Individual method
    location = bot.find_relative_image(
        anchor_image='warning.png',      # Unique anchor image
        target_image='ok_button.png',    # Target that may have duplicates
        max_distance=200,                # Maximum distance of 200px
        confidence=0.9
    )

    # Relative image click
    success = bot.click_relative_image(
        anchor_image='warning.png',
        target_image='ok_button.png',
        max_distance=150,
        backtrack=True                   # Smart retry
    )

    # ===== NEW FEATURE 2: CLICK ON COORDINATES =====
    print("2. CLICK ON SPECIFIC COORDINATES")

    success = bot.click_coordinates(
        x=500, y=300,                    # Exact position
        delay=1,
        mouse_button="right",            # Right click
        backtrack=True
    )

    # ===== NEW FEATURE 3: ADVANCED TYPING =====
    print("3. TYPING WITH SPECIAL COMMANDS")

    success = bot.type_text(
        text="{ctrl}a{del}New text{tab}Next{enter}",
        interval=0.05,
        backtrack=True
    )

    # ===== NEW FEATURE 4: KEYBOARD COMMANDS =====
    print("4. EXPANDED KEYBOARD COMMANDS")

    # Specific command
    success = bot.keyboard_command("Ctrl+S", delay=1, backtrack=True)
    success = bot.keyboard_command("F7", backtrack=True)      # Oracle Forms
    success = bot.keyboard_command("Alt+Tab", backtrack=True)  # Switch window

    # See all available commands
    commands = bot.get_available_keyboard_commands()
    print(f"Total commands: {len(commands)}")

    # ===== USING EVERYTHING IN A TASK LIST =====
    print("5. ALL FEATURES IN A LIST")

    complete_tasks = [
        # Traditional text
        {
            'text': 'Login',
            'region': (100, 100, 500, 300),
            'char_type': 'letters',
            'backtrack': True,
            'sendtext': 'admin{tab}password'
        },

        # RELATIVE IMAGE
        {
            'type': 'relative_image',
            'anchor_image': 'dialog.png',
            'target_image': 'close.png',
            'max_distance': 200,
            'confidence': 0.9,
            'backtrack': True
        },

        # CLICK ON COORDINATES
        {
            'type': 'click',
            'x': 400,
            'y': 250,
            'mouse_button': 'left',
            'backtrack': True
        },

        # DIRECT TYPING
        {
            'type': 'type_text',
            'text': 'Advanced automation!',
            'interval': 0.05
        },

        # KEYBOARD COMMAND
        {
            'type': 'keyboard_command',
            'command': 'Ctrl+S',
            'delay': 1
        },

        # Traditional image
        {
            'image': 'confirm.png',
            'confidence': 0.9,
            'backtrack': True
        }
    ]

    # Run everything
    results = execute_tasks(complete_tasks)

    successful = sum(1 for r in results if r.success)
    print(f"{successful}/{len(results)} tasks executed successfully")


def standalone_functions_example():
    """Standalone functions - quick use without instantiating a class."""

    print("6. STANDALONE FUNCTIONS (WITHOUT INSTANTIATING A CLASS)")

    from visus.desktop import (
        # Traditional
        find_text, click_text, find_image, click_image,
        # NEW
        find_relative_image, click_relative_image,
        click_coordinates, type_text_standalone,
        keyboard_command_standalone, get_available_keyboard_commands
    )

    # Quick use of the new features
    location = find_relative_image("anchor.png", "target.png")
    success = click_relative_image("anchor.png", "target.png", backtrack=True)
    success = click_coordinates(100, 200, backtrack=True)
    success = type_text_standalone("{ctrl}a{del}Test", backtrack=True)
    success = keyboard_command_standalone("Ctrl+S", backtrack=True)

    commands = get_available_keyboard_commands()
    print(f"Available commands: {len(commands)}")


def improved_backtrack_example():
    """Improved backtrack system between individual methods."""

    print("7. SMART BACKTRACK BETWEEN METHODS")

    from visus.desktop import VisusBot

    bot = VisusBot()

    # Option 1: Automatic backtrack
    success1 = bot.click_image('step1.png', backtrack=True)
    success2 = bot.click_text('Next', backtrack=True)          # If it fails, go back to step1
    success3 = bot.click_coordinates(100, 200, backtrack=True)  # If it fails, go back to Next

    # Option 2: Manual session control
    bot.start_task_session()

    bot.click_image('login.png', backtrack=True)
    bot.type_text('username{tab}password', backtrack=True)
    bot.keyboard_command('Enter', backtrack=True)
    bot.click_relative_image('dialog.png', 'ok.png', backtrack=True)

    successful, total = bot.end_task_session()
    print(f"Session finished: {successful}/{total} successful")


def before_after_comparison():
    """Direct comparison: before vs after the new features."""

    print("\n" + "=" * 80)
    print("COMPARISON: BEFORE vs AFTER the new features")
    print("=" * 80)

    print("\nBEFORE (Limitations):")
    print("   - Only basic text and image")
    print("   - No relative image (issues with duplicates)")
    print("   - No click on specific coordinates")
    print("   - Limited keyboard commands")
    print("   - No typing with special commands")
    print("   - Backtrack only in lists")

    print("\nAFTER (New Features):")
    print("   - Relative image (anchor + target)")
    print("   - Click on specific coordinates")
    print("   - 100+ predefined keyboard commands")
    print("   - Typing with special commands {ctrl}a{del}text{enter}")
    print("   - Backtrack between individual methods")
    print("   - Standalone functions for quick use")
    print("   - 6 different task types")
    print("   - Full backward compatibility with old code")

    print("\nSOLVED USE CASES:")
    print("   1. Multiple 'OK' buttons -> Relative image solves it!")
    print("   2. Click at a fixed position -> Specific coordinates!")
    print("   3. F1-F12, Ctrl+S commands -> Expanded list!")
    print("   4. Select all and type -> {ctrl}a{del}text!")
    print("   5. Smart retry -> Individual backtrack!")


if __name__ == "__main__":
    print("MIGRATION GUIDE - Visus Desktop")
    print("Demonstrating ALL the new features")
    print("=" * 80)

    try:
        # Show the new code
        new_code_example()

        # Standalone functions
        standalone_functions_example()

        # Improved backtrack
        improved_backtrack_example()

        # Comparison
        before_after_comparison()

        print("\nMIGRATION COMPLETE!")
        print("You now have access to ALL the advanced features!")

    except Exception as e:
        print(f"\nError: {e}")
        print("This is just a migration example. Adapt it to your needs.")
