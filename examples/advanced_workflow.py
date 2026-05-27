"""
Advanced example: Complex automation workflow using visus-desktop.

This example demonstrates:
1. Multi-step workflows
2. Error handling and retries
3. Custom configuration
4. Region-based searching
5. Conditional task execution
"""

import time
from visus.desktop import VisusBot
from visus.desktop import BotVisionConfig
from visus.desktop.exceptions import TaskExecutionError, TextNotFoundError


def create_web_login_workflow():
    """Create a workflow for web application login.

    A workflow is simply a list of task dictionaries executed in order.
    """
    return [
        # Navigate to the login page (top banner area)
        {
            "text": "Sign In",
            "region": (0, 0, 1920, 200),
        },
        # Enter credentials (center area)
        {
            "text": "Username",
            "region": (400, 200, 1120, 600),
        },
        # Note: in real automation you would add a 'sendtext' field to type
        # into the field after clicking it.
        {
            "text": "Password",
            "region": (400, 200, 1120, 600),
        },
        # Submit the login form (lower center)
        {
            "text": "Log In",
            "region": (400, 400, 1120, 800),
        },
        # Verify successful login (full screen)
        {
            "text": "Dashboard",
            "region": (0, 0, 1920, 1080),
        },
    ]


def create_form_filling_workflow():
    """Create a workflow for filling out a form."""
    return [
        # Locate the form on the page
        {
            "text": "Contact Form",
            "region": (0, 0, 1920, 400),
        },
        # Fill in the name field
        {
            "text": "Full Name",
            "region": (200, 200, 1720, 800),
        },
        # Fill in the email field
        {
            "text": "Email",
            "region": (200, 200, 1720, 800),
        },
        # Submit the form
        {
            "text": "Submit",
            "region": (200, 600, 1720, 1000),
        },
    ]


def execute_workflow_with_error_handling(bot, workflow, workflow_name):
    """Execute a workflow with comprehensive error handling."""
    print(f"\n{'=' * 50}")
    print(f"Executing workflow: {workflow_name}")
    print(f"{'=' * 50}")

    try:
        results = bot.execute_tasks(workflow)

        # Analyze results. execute_tasks returns a list of TaskResult objects.
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = total_tasks - successful_tasks

        print(f"\nWorkflow Summary:")
        print(f"  Total tasks: {total_tasks}")
        print(f"  Successful: {successful_tasks}")
        print(f"  Failed: {failed_tasks}")
        if total_tasks:
            print(f"  Success rate: {(successful_tasks / total_tasks) * 100:.1f}%")

        # Detailed results
        print(f"\nDetailed Results:")
        for i, result in enumerate(results, 1):
            status = "PASSED" if result.success else "FAILED"
            print(f"  {i}. {result.task_name}: {status}")

            if not result.success:
                error_msg = result.error or "Unknown error"
                print(f"     Error: {error_msg}")

                # Optional: add retry logic here
                print(f"     Suggestion: check if UI elements are visible")

        return results

    except (TaskExecutionError, TextNotFoundError) as e:
        print(f"Workflow execution failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during workflow execution: {e}")
        return None


def demonstrate_configuration_options():
    """Demonstrate different configuration options."""
    print("\n" + "=" * 50)
    print("Configuration Options Demo")
    print("=" * 50)

    # High precision configuration. BotVisionConfig takes a single dict.
    high_precision_config = BotVisionConfig({
        "confidence_threshold": 95.0,
        "retry_attempts": 1,
        "default_delay": 0.5,
        "log_level": "ERROR",
    })

    # Robust configuration (more forgiving)
    robust_config = BotVisionConfig({
        "confidence_threshold": 70.0,
        "retry_attempts": 5,
        "default_delay": 2.0,
        "log_level": "DEBUG",
    })

    configs = [
        ("High Precision", high_precision_config),
        ("Robust/Forgiving", robust_config),
    ]

    for config_name, config in configs:
        print(f"\n{config_name} Configuration:")
        print(f"  Confidence threshold: {config.confidence_threshold}")
        print(f"  Retry attempts: {config.retry_attempts}")
        print(f"  Default delay: {config.default_delay}s")
        print(f"  Log level: {config.log_level}")


def main():
    """Main function demonstrating advanced usage."""
    print("Visus Desktop - Advanced Example")
    print("This example shows complex workflows and error handling")

    # Show configuration options
    demonstrate_configuration_options()

    # Create bot with a robust configuration for the demo
    config = BotVisionConfig({
        "confidence_threshold": 80.0,
        "retry_attempts": 3,
        "default_delay": 1.5,
        "log_level": "DEBUG",
    })

    bot = VisusBot(config=config)

    # Create workflows
    workflows = [
        ("Web Login Workflow", create_web_login_workflow()),
        ("Form Filling Workflow", create_form_filling_workflow()),
    ]

    # Execute each workflow
    all_results = {}

    for workflow_name, workflow in workflows:
        print(f"\nPreparing to execute: {workflow_name}")
        print("Note: this is a demonstration - actual UI elements may not be present")

        # Add a small delay to show workflow execution
        time.sleep(1)

        results = execute_workflow_with_error_handling(bot, workflow, workflow_name)
        all_results[workflow_name] = results

        # Pause between workflows
        if workflow_name != workflows[-1][0]:  # Not the last workflow
            print("\nPausing before next workflow...")
            time.sleep(2)

    # Final summary
    print(f"\n{'=' * 60}")
    print("FINAL EXECUTION SUMMARY")
    print(f"{'=' * 60}")

    for workflow_name, results in all_results.items():
        if results:
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)
            print(f"{workflow_name}: {success_count}/{total_count} tasks successful")
        else:
            print(f"{workflow_name}: Workflow failed to execute")

    print("\nTips for better automation:")
    print("   1. Use specific regions to improve accuracy")
    print("   2. Adjust confidence threshold based on your needs")
    print("   3. Enable verbose logging during development")
    print("   4. Handle errors gracefully in production")
    print("   5. Test workflows on consistent UI states")


if __name__ == "__main__":
    main()
