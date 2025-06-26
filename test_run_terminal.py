import time
from agent import DesktopAgent
from task_interpreter import TaskInterpreter

# Create the agent
agent = DesktopAgent()

# Create the interpreter
interpreter = TaskInterpreter(agent)

# Test the run terminal task directly
print("Testing 'run terminal' task...")
success = interpreter._run_terminal()
print(f"Task completed with success: {success}")

# Keep the script running for a moment to see the results
time.sleep(5) 