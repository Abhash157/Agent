import os
import time
import json
import openai
import numpy as np
import cv2
import pyautogui
import pytesseract
from PIL import Image
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()]
)
logger = logging.getLogger("DesktopAgent")

class DesktopAgent:
    """Autonomous desktop agent that can perform tasks by controlling the screen."""
    
    def __init__(self, openai_api_key=None):
        """Initialize the desktop agent with necessary components."""
        # Initialize OpenAI if API key is provided
        self.llm_available = False
        if openai_api_key or os.environ.get("OPENAI_API_KEY"):
            openai.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            self.llm_available = True
            logger.info("LLM integration enabled")
        
        # Initialize screen perception
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
        # Load UI element detection from existing code
        from refined import find_internal_containers
        self.find_internal_containers = find_internal_containers
        
        # Task state
        self.current_task = None
        self.task_status = "idle"
        self.task_steps = []
        self.current_step_index = 0
        
        logger.info("Desktop Agent initialized successfully")
    
    def take_screenshot(self, region=None):
        """Take a screenshot of the entire screen or a specific region."""
        try:
            if region:
                return pyautogui.screenshot(region=region)
            else:
                return pyautogui.screenshot()
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def move_mouse(self, x, y, duration=0.5):
        """Move the mouse to the specified coordinates with smooth movement."""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            logger.info(f"Moved mouse to ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def click(self, x=None, y=None, button='left'):
        """Click at the current position or specified coordinates."""
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
                logger.info(f"Clicked at ({x}, {y}) with {button} button")
            else:
                pyautogui.click(button=button)
                current_pos = pyautogui.position()
                logger.info(f"Clicked at current position {current_pos} with {button} button")
            return True
        except Exception as e:
            logger.error(f"Failed to click: {e}")
            return False
    
    def type_text(self, text, interval=0.01):
        """Type the specified text with a natural typing speed."""
        try:
            pyautogui.typewrite(text, interval=interval)
            logger.info(f"Typed text: {text[:20]}{'...' if len(text) > 20 else ''}")
            return True
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def press_key(self, key):
        """Press a single key or key combination."""
        try:
            pyautogui.press(key)
            logger.info(f"Pressed key: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return False
    
    def analyze_screen(self):
        """Analyze the current screen to identify UI elements and text."""
        screenshot = self.take_screenshot()
        if screenshot is None:
            return None
        
        # Convert PIL image to OpenCV format
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Find UI containers
        processed_img, containers = self.find_internal_containers(screenshot_cv)
        
        # Extract text from containers
        elements = []
        for i, (x, y, w, h) in enumerate(containers):
            roi = screenshot.crop((x, y, x + w, y + h))
            text = pytesseract.image_to_string(roi).strip()
            elements.append({
                "id": i,
                "type": "container",
                "bounds": (x, y, w, h),
                "text": text
            })
        
        logger.info(f"Analyzed screen and found {len(elements)} UI elements")
        return {
            "screenshot": screenshot,
            "elements": elements
        }
    
    def find_element_by_text(self, text, partial_match=True):
        """Find UI element containing the specified text."""
        screen_data = self.analyze_screen()
        if not screen_data:
            return None
        
        for element in screen_data["elements"]:
            element_text = element.get("text", "")
            if (partial_match and text.lower() in element_text.lower()) or \
               (not partial_match and text.lower() == element_text.lower()):
                logger.info(f"Found element with text '{text}': {element}")
                return element
        
        logger.info(f"No element found with text '{text}'")
        return None
    
    def click_element_with_text(self, text, partial_match=True):
        """Find and click on a UI element containing the specified text."""
        element = self.find_element_by_text(text, partial_match)
        if element:
            x, y, w, h = element["bounds"]
            center_x = x + w // 2
            center_y = y + h // 2
            return self.click(center_x, center_y)
        return False
    
    def plan_task(self, task_description):
        """Use LLM to break down the task into actionable steps."""
        if not self.llm_available:
            logger.warning("LLM not available for task planning. Set OPENAI_API_KEY environment variable.")
            return ["Analyze screen", "Perform actions based on visual feedback"]
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI desktop automation assistant. Break down user tasks into concrete steps that can be performed using mouse clicks, keyboard input, and screen reading."},
                    {"role": "user", "content": f"Task: {task_description}\nBreak this down into a sequence of specific steps."}
                ]
            )
            steps = response.choices[0].message.content.strip().split("\n")
            # Clean up steps (remove numbering, etc.)
            steps = [step.strip() for step in steps]
            steps = [step[step.find(" ")+1:] if step.find(".") > 0 and step.find(" ") > 0 else step for step in steps]
            steps = [step for step in steps if step]  # Remove empty steps
            
            logger.info(f"Planned task with {len(steps)} steps")
            return steps
        except Exception as e:
            logger.error(f"Failed to plan task with LLM: {e}")
            return ["Analyze screen", "Perform actions based on visual feedback"]
    
    def execute_task(self, task_description):
        """Execute a task by planning and executing steps."""
        logger.info(f"Starting task: {task_description}")
        self.current_task = task_description
        self.task_status = "planning"
        
        # Plan task steps
        self.task_steps = self.plan_task(task_description)
        self.current_step_index = 0
        self.task_status = "executing"
        
        # Execute each step
        for i, step in enumerate(self.task_steps):
            self.current_step_index = i
            logger.info(f"Executing step {i+1}/{len(self.task_steps)}: {step}")
            
            # Execute step (in a real implementation, this would interpret and execute the step)
            time.sleep(1)  # Placeholder for actual execution
            
            # Check if step succeeded (would be based on visual feedback in real implementation)
            success = True  # Placeholder
            
            if not success:
                self.task_status = "failed"
                logger.error(f"Failed to execute step: {step}")
                return False
        
        self.task_status = "completed"
        logger.info(f"Task completed successfully")
        return True

# Example usage
if __name__ == "__main__":
    agent = DesktopAgent()
    
    # Example: find and click a button
    element = agent.find_element_by_text("Submit")
    if element:
        x, y, w, h = element["bounds"]
        agent.click(x + w//2, y + h//2)
    
    # Example: execute a complex task
    #agent.execute_task("Open Firefox, go to gmail.com, and check for new emails") 