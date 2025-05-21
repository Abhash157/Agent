# Autonomous Desktop Agent

An intelligent agent that can control your desktop to perform tasks autonomously, like a personal digital assistant.

## Features

- **Computer Vision**: Detects UI elements (buttons, text fields, etc.) on the screen
- **Text Recognition**: Uses OCR to read text from UI elements
- **Task Planning**: Breaks down complex tasks into simple steps
- **Autonomous Control**: Executes tasks by controlling the mouse and keyboard
- **LLM Integration**: Uses OpenAI's GPT-4 for advanced task understanding (optional)

## Requirements

- Python 3.7+
- X11 display server (Linux)
- OpenAI API key (optional, for advanced task planning)

## Installation

1. Install the required system dependencies:

```bash
# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y python3-pip python3-tk tesseract-ocr python3-xlib

# For Arch Linux
sudo pacman -S python-pip tk tesseract python-xlib
```

2. Install the Python dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key (optional):

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

1. Run the desktop agent:

```bash
python main.py
```

2. Enter a task in the input field and click "Run Task"

Example tasks:
- "Open Firefox and go to gmail.com"
- "Find the weather forecast for today"
- "Create a new text file on the desktop and write 'Hello World'"

## How It Works

1. **Task Planning**: The agent breaks down your task into a sequence of steps
2. **Screen Analysis**: It captures the screen and identifies UI elements
3. **Task Execution**: It executes each step by controlling the mouse and keyboard
4. **Feedback Loop**: It checks the results of each action and adjusts as needed

## Extending the Agent

You can extend the agent by:

1. Adding new action patterns in `task_interpreter.py`
2. Improving the UI element detection in `refined.py`
3. Adding specialized modules for specific applications

## Troubleshooting

- If the agent can't find UI elements, try adjusting the detection thresholds in `refined.py`
- For Linux systems, ensure you're running an X11 session
- Check the agent.log file for detailed error messages

## License

MIT

## Disclaimer

This software automates UI interactions. Use at your own risk. Always maintain the ability to quickly interrupt the agent using the Stop button if it performs unintended actions. 