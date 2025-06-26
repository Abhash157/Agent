# Autonomous Desktop Agent - Usage Guide

## Current Status

The agent is currently in development and has the following capabilities:

1. **Basic UI**: A Tkinter interface for entering tasks and viewing agent output
2. **Task Planning**: Can break down tasks into steps (requires OpenAI API key for advanced planning)
3. **Screen Analysis**: Can take screenshots and attempt to detect UI elements
4. **Task Execution**: Can execute some basic tasks like "run terminal"

## Known Issues

1. **Screenshot Issues on Wayland**: The agent may have difficulty capturing screenshots on Wayland. It attempts to use `grim` if available, then falls back to `pyautogui`.
2. **UI Element Detection**: The current UI element detection is limited and may not detect all elements correctly.
3. **Task Planning**: Without an OpenAI API key, the agent falls back to generic steps.

## How to Use

1. **Start the Agent**:
   ```
   python main.py
   ```

2. **Enter a Task**:
   Enter a task in the text field and click "Run Task" or press Enter.

3. **Supported Tasks**:
   - "run terminal" - Opens a terminal window
   - Other tasks will be broken down into generic steps if no OpenAI API key is provided

4. **Setting OpenAI API Key**:
   To enable advanced task planning, set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY="your-api-key-here"
   ```

## Troubleshooting

1. **Blank Screenshots**:
   - Ensure you have the appropriate screenshot utilities installed for your desktop environment
   - For Wayland, install `grim`: `sudo pacman -S grim`

2. **No UI Elements Detected**:
   - The agent saves debug screenshots to `debug_screenshot_for_analysis.png` and `debug_processed_screenshot.png`
   - Check these files to see if the screenshots are being captured correctly

3. **Task Execution Fails**:
   - Check the console output for error messages
   - Try running the task directly using a test script (see `test_run_terminal.py` for an example)

## Next Steps for Development

1. Improve UI element detection
2. Add more direct task handlers
3. Implement better error recovery
4. Add support for more complex tasks 