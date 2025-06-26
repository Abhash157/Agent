import re
import time
import openai
import logging
import pyautogui

logger = logging.getLogger("TaskInterpreter")

class TaskInterpreter:
    """Interprets and executes tasks described in natural language."""
    
    def __init__(self, agent, openai_api_key=None):
        """Initialize the task interpreter with a reference to the desktop agent."""
        self.agent = agent
        self.openai_api_key = openai_api_key
        
        # Define action patterns for common operations
        self.action_patterns = [
            # Specific task patterns
            (r"run\s(?:the\s)?terminal", self._run_terminal),
            
            # General action patterns
            (r"click(?:\son)?\s(?:the\s)?(?:button\s)?['\"]?(.*?)['\"]?", self._click_element),
            (r"type\s['\"]?(.*?)['\"]?\s(?:into|in)\s(?:the\s)?(?:field\s)?['\"]?(.*?)['\"]?", self._type_into_field),
            (r"press\s(?:the\s)?(?:key\s)?['\"]?(.*?)['\"]?", self._press_key),
            (r"open\s(?:the\s)?(?:app\s|application\s)?['\"]?(.*?)['\"]?", self._open_application),
            (r"wait\s(?:for\s)?(\d+)(?:\s?seconds?)?", self._wait),
            (r"scroll\s(up|down)(?:\sby\s(\d+))?", self._scroll),
            (r"search\s(?:for\s)?['\"]?(.*?)['\"]?", self._search),
            # Add handlers for high-level steps that are commonly used in fallback planning
            (r"analyze\s(?:the\s)?screen", self._analyze_screen),
            (r"perform\s(?:actions|tasks)(?:\sbased\son\s(?:visual\s)?feedback)?", self._perform_actions)
        ]
    
    def interpret_step(self, step_description):
        """Interpret a natural language step description and execute it."""
        logger.info(f"Interpreting step: {step_description}")
        
        # Check for matches with our action patterns
        for pattern, action_func in self.action_patterns:
            match = re.search(pattern, step_description, re.IGNORECASE)
            if match:
                logger.info(f"Matched pattern: {pattern}")
                return action_func(*match.groups())
        
        # If no pattern matches, use LLM to interpret the step if available
        if self.agent.llm_available:
            return self._interpret_with_llm(step_description)
        
        # Fallback: Try to find any UI element that might match
        logger.warning(f"No pattern matched for step: {step_description}")
        words = step_description.split()
        for word in words:
            if len(word) > 3:  # Avoid short words
                element = self.agent.find_element_by_text(word)
                if element:
                    logger.info(f"Found UI element with text: {word}")
                    x, y, w, h = element["bounds"]
                    return self.agent.click(x + w//2, y + h//2)
        
        logger.error(f"Could not interpret step: {step_description}")
        return False
    
    def _click_element(self, element_text):
        """Click on an element with the specified text."""
        return self.agent.click_element_with_text(element_text)
    
    def _type_into_field(self, text, field_name):
        """Type text into a field identified by its name/label."""
        # First find and click the field
        if not self.agent.click_element_with_text(field_name):
            logger.error(f"Could not find field: {field_name}")
            return False
        
        # Then type the text
        time.sleep(0.5)  # Wait for field to be active
        return self.agent.type_text(text)
    
    def _press_key(self, key):
        """Press a specified key."""
        return self.agent.press_key(key)
    
    def _open_application(self, app_name):
        """Open an application by name."""
        # This is platform-dependent, for Linux we'll try to use the command line
        try:
            import subprocess
            subprocess.Popen([app_name.lower()], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Launched application: {app_name}")
            time.sleep(2)  # Wait for app to start
            return True
        except Exception as e:
            logger.error(f"Failed to open application {app_name}: {e}")
            return False
    
    def _wait(self, seconds):
        """Wait for the specified number of seconds."""
        try:
            seconds = int(seconds)
            logger.info(f"Waiting for {seconds} seconds")
            time.sleep(seconds)
            return True
        except ValueError:
            logger.error(f"Invalid wait time: {seconds}")
            return False
    
    def _scroll(self, direction, amount=None):
        """Scroll in the specified direction."""
        try:
            clicks = 5  # Default scroll amount
            if amount:
                clicks = int(amount)
            
            if direction.lower() == "down":
                self.agent.press_key("pagedown")
            else:
                self.agent.press_key("pageup")
            
            logger.info(f"Scrolled {direction} by {clicks} clicks")
            return True
        except Exception as e:
            logger.error(f"Failed to scroll {direction}: {e}")
            return False
    
    def _search(self, query):
        """Perform a search with the given query."""
        # First look for a search field
        search_field = self.agent.find_element_by_text("Search")
        if search_field:
            x, y, w, h = search_field["bounds"]
            self.agent.click(x + w//2, y + h//2)
            time.sleep(0.5)
            self.agent.type_text(query)
            self.agent.press_key("enter")
            return True
        
        # Try typing the query directly and pressing enter
        self.agent.type_text(query)
        self.agent.press_key("enter")
        return True
    
    def _analyze_screen(self, *args):
        """Handle the 'analyze screen' step."""
        logger.info("Executing analyze screen step")
        
        # Take a screenshot and analyze it
        screen_data = self.agent.analyze_screen()
        
        if not screen_data or not screen_data.get("elements"):
            logger.warning("No UI elements found during screen analysis")
            # Even if no elements were found, we consider this step successful
            # because the analysis was performed
            return True
        
        # Log information about found elements
        elements = screen_data.get("elements", [])
        logger.info(f"Found {len(elements)} UI elements during screen analysis")
        
        for i, element in enumerate(elements):
            text = element.get("text", "").strip()
            if text:
                logger.info(f"Element {i}: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        return True
    
    def _perform_actions(self, *args):
        """Handle the 'perform actions based on visual feedback' step."""
        logger.info("Executing perform actions step")
        
        # Take a screenshot and analyze it
        screen_data = self.agent.analyze_screen()
        
        if not screen_data or not screen_data.get("elements"):
            logger.warning("No UI elements found for action")
            return False
        
        # Look for actionable elements (buttons, links, etc.)
        elements = screen_data.get("elements", [])
        actionable_keywords = ["submit", "ok", "yes", "continue", "next", "start", 
                              "login", "sign in", "search", "send", "apply"]
        
        # Try to find and click on an actionable element
        for keyword in actionable_keywords:
            for element in elements:
                text = element.get("text", "").lower()
                if keyword in text:
                    logger.info(f"Found actionable element with text containing '{keyword}'")
                    x, y, w, h = element["bounds"]
                    center_x = x + w // 2
                    center_y = y + h // 2
                    return self.agent.click(center_x, center_y)
        
        # If no actionable element found, try clicking on the first element with text
        for element in elements:
            if element.get("text", "").strip():
                logger.info("No specific actionable element found, clicking on first element with text")
                x, y, w, h = element["bounds"]
                center_x = x + w // 2
                center_y = y + h // 2
                return self.agent.click(center_x, center_y)
        
        logger.warning("No suitable elements found for action")
        return False
    
    def _interpret_with_llm(self, step_description):
        """Use LLM to interpret complex steps."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI desktop automation interpreter. Translate the user's instruction into a sequence of mouse and keyboard operations."},
                    {"role": "user", "content": f"Instruction: {step_description}\nTranslate this into a sequence of basic operations (click, type, press key, etc.)."}
                ]
            )
            interpretation = response.choices[0].message.content.strip()
            logger.info(f"LLM interpretation: {interpretation}")
            
            # Execute each sub-step from the LLM
            steps = interpretation.split("\n")
            success = True
            for sub_step in steps:
                if sub_step.strip():
                    # Recursively interpret each sub-step
                    sub_success = self.interpret_step(sub_step)
                    if not sub_success:
                        success = False
            
            return success
        except Exception as e:
            logger.error(f"Failed to interpret step with LLM: {e}")
            return False
    
    def _run_terminal(self, *args):
        """Handle the 'run terminal' task."""
        logger.info("Executing run terminal task")
        
        # Method 1: Try using keyboard shortcut (Ctrl+Alt+T on many Linux systems)
        try:
            # Press Ctrl+Alt+T to open terminal
            pyautogui.hotkey('ctrl', 'alt', 't')
            logger.info("Pressed Ctrl+Alt+T to open terminal")
            time.sleep(2)  # Wait for terminal to open
            return True
        except Exception as e:
            logger.error(f"Failed to use keyboard shortcut: {e}")
        
        # Method 2: Try using application launcher
        try:
            # Press Super (Windows) key to open application launcher
            pyautogui.press('win')
            time.sleep(1)
            
            # Type 'terminal' and press Enter
            self.agent.type_text('terminal')
            time.sleep(0.5)
            self.agent.press_key('enter')
            logger.info("Used application launcher to open terminal")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to use application launcher: {e}")
        
        # Method 3: Try using subprocess to run terminal directly
        try:
            import subprocess
            # Try common terminal commands
            for cmd in ['gnome-terminal', 'konsole', 'xterm', 'terminator', 'alacritty']:
                try:
                    subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    logger.info(f"Launched terminal using command: {cmd}")
                    time.sleep(2)
                    return True
                except FileNotFoundError:
                    continue
        except Exception as e:
            logger.error(f"Failed to launch terminal using subprocess: {e}")
        
        logger.error("Failed to run terminal using all methods")
        return False 