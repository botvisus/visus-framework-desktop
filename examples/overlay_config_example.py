"""
Overlay configuration example - Visus Desktop

This example demonstrates how to use the overlay configuration options.
"""

from visus.desktop import VisusBot


def overlay_configuration_example():
    """Demonstrate how to configure the overlay."""
    print("OVERLAY CONFIGURATION EXAMPLE")
    print("=" * 50)

    # Method 1: Configuration via dictionary at initialization
    print("\nMethod 1: Configuration at initialization")
    config = {
        "confidence_threshold": 85.0,
        "retry_attempts": 3,
        "overlay_duration": 2000,     # 2 seconds
        "overlay_color": "blue",      # Blue
        "overlay_width": 6,           # Thicker line
        "show_overlay": True,         # Master toggle: show the overlay
        "ocr_languages": ["eng"],
        "log_level": "INFO"
    }

    bot1 = VisusBot(config)
    print("Bot created with BLUE overlay, 2 seconds, thick line")
    print(f"Configuration: {bot1.get_overlay_config()}")

    # Method 2: Configuration after initialization
    print("\nMethod 2: Configuration after initialization")
    bot2 = VisusBot()
    bot2.configure_overlay(
        enabled=True,
        color="green",
        duration=1500,  # 1.5 seconds
        width=8
    )
    print("Bot configured with GREEN overlay, 1.5 seconds, extra-thick line")
    print(f"Configuration: {bot2.get_overlay_config()}")

    # Method 3: Individual properties
    print("\nMethod 3: Individual properties")
    bot3 = VisusBot()
    bot3.show_overlay = True
    bot3.config.config["overlay_color"] = "purple"
    bot3.config.config["overlay_duration"] = 3000  # 3 seconds
    print("Bot configured with PURPLE overlay, 3 seconds")
    print(f"Configuration: {bot3.get_overlay_config()}")

    # Method 4: Disable the overlay
    print("\nMethod 4: Disable the overlay")
    bot4 = VisusBot()
    bot4.configure_overlay(enabled=False)
    print("Bot with overlay disabled")
    print(f"Configuration: {bot4.get_overlay_config()}")

    print("\n" + "=" * 50)
    print("OPTIONS SUMMARY:")
    print("=" * 50)
    print("AVAILABLE SETTINGS:")
    print("   - show_overlay: True/False - master toggle (turns the overlay on/off)")
    print("   - overlay_color: 'red', 'blue', 'green', 'yellow', etc.")
    print("   - overlay_duration: 1000, 2000, 3000... (milliseconds)")
    print("   - overlay_width: 4, 6, 8... (line thickness)")

    print("\nAVAILABLE COLORS:")
    print("   - red, blue, green, yellow")
    print("   - purple, orange, cyan, magenta")
    print("   - white, black")

    print("\nTIPS:")
    print("   - For production: set show_overlay=False")
    print("   - For debugging: use vivid colors and a longer duration")
    print("   - For fast automation: shorter duration (500-1000ms)")


def practical_usage_example():
    """Practical usage example."""
    print("\n\nPRACTICAL EXAMPLE")
    print("=" * 50)

    # Configuration for development/debugging
    debug_config = {
        "overlay_duration": 2000,
        "overlay_color": "blue",
        "overlay_width": 6,
        "show_overlay": True,
        "log_level": "DEBUG"
    }

    bot = VisusBot(debug_config)

    print("Bot configured for debugging:")
    print("   - Blue overlay, 2 seconds, thick line")
    print("   - Perfect for seeing where it is clicking")

    print("\nUsage example:")
    print("   bot = VisusBot(debug_config)")
    print("   bot.click_text('Login')  # Shows a blue overlay before the click")
    print("   bot.click_image('button.png')  # Overlay appears on the found image")

    # Configuration for production
    print("\nFor production (no overlay):")
    prod_config = {
        "show_overlay": False,
        "log_level": "ERROR"
    }

    print("   prod_bot = VisusBot(prod_config)")
    print("   # Fast execution without visual feedback")


def overlay_colors_example():
    """Demonstrate all available colors."""
    print("\nOVERLAY COLORS EXAMPLE")
    print("=" * 50)

    from visus.desktop import VisusBot

    # List available colors
    available_colors = VisusBot.get_available_overlay_colors()
    print("Available colors:")
    for i, color in enumerate(available_colors, 1):
        print(f"   {i:2d}. {color}")

    # Configurations for each color
    print("\nConfiguration examples:")

    example_configurations = [
        {"color": "red", "desc": "Red - default, good visibility"},
        {"color": "blue", "desc": "Blue - professional, soft"},
        {"color": "green", "desc": "Green - success, nature"},
        {"color": "yellow", "desc": "Yellow - attention, highlight"},
        {"color": "purple", "desc": "Purple - creative, distinctive"},
        {"color": "orange", "desc": "Orange - energetic, vibrant"},
        {"color": "cyan", "desc": "Cyan - technological, modern"},
        {"color": "magenta", "desc": "Magenta - strong, eye-catching"},
        {"color": "white", "desc": "White - minimalist, high contrast"},
        {"color": "black", "desc": "Black - elegant, discreet"}
    ]

    for config in example_configurations:
        print(f"   - {config['color']:8} - {config['desc']}")

    print("\nUsage example:")
    print("   bot = VisusBot()")
    print("   bot.configure_overlay(color='blue', duration=2000)")
    print("   bot.configure_overlay(color='green', width=8)")

    # Color validation
    print("\nAutomatic validation:")
    try:
        bot = VisusBot()
        bot.configure_overlay(color="azul")  # Will raise an error (invalid color)
    except ValueError as e:
        print(f"   Caught error: {e}")

    print("   Use only the colors listed above!")


def visual_test_example():
    """Example for testing colors visually."""
    print("\nVISUAL COLOR TEST")
    print("=" * 50)

    from visus.desktop import VisusBot

    print("To test all colors visually:")
    print("   bot = VisusBot()")
    print("   bot.test_overlay_colors()  # Shows each color for 1.5s")
    print("   bot.test_overlay_colors(duration=3000)  # 3 seconds each")

    print("\nTo test a specific color:")
    print("   bot.configure_overlay(color='blue', duration=2000)")
    print("   # Now every click will show a blue overlay")


def practical_configurations_example():
    """Practical configuration examples."""
    print("\nPRACTICAL CONFIGURATIONS")
    print("=" * 50)

    configs = {
        "Intensive Debug": {
            "overlay_color": "red",
            "overlay_duration": 3000,
            "overlay_width": 8,
            "show_overlay": True,
            "desc": "For detailed debugging - red, 3s, thick line"
        },

        "Development": {
            "overlay_color": "blue",
            "overlay_duration": 1500,
            "overlay_width": 6,
            "show_overlay": True,
            "desc": "For development - blue, 1.5s, visible"
        },

        "Quick Test": {
            "overlay_color": "green",
            "overlay_duration": 800,
            "overlay_width": 4,
            "show_overlay": True,
            "desc": "For quick tests - green, 0.8s"
        },

        "Demonstration": {
            "overlay_color": "yellow",
            "overlay_duration": 2500,
            "overlay_width": 10,
            "show_overlay": True,
            "desc": "For demonstrations - yellow, 2.5s, very visible"
        },

        "Production": {
            "show_overlay": False,
            "desc": "For production - no overlay, maximum speed"
        }
    }

    for name, config in configs.items():
        print(f"\n{name}:")
        print(f"   {config['desc']}")

        # Remove desc to show a clean config
        clean_config = {k: v for k, v in config.items() if k != 'desc'}

        print(f"   Configuration: {clean_config}")
        print(f"   Usage: bot = VisusBot({clean_config})")


if __name__ == "__main__":
    overlay_configuration_example()
    overlay_colors_example()
    visual_test_example()
    practical_configurations_example()
    practical_usage_example()

    print("\nFINAL SUMMARY")
    print("=" * 50)
    print("10 colors available: red, blue, green, yellow, purple, orange, cyan, magenta, white, black")
    print("Automatic parameter validation")
    print("Convenient methods for configuration")
    print("Visual test function: bot.test_overlay_colors()")
    print("Practical configurations for different scenarios")

    print("\nFINAL TIP:")
    print("   Use VisusBot.get_available_overlay_colors() to see all the options!")
