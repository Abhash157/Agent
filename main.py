import os
import sys
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import logging
from agent import DesktopAgent
from task_interpreter import TaskInterpreter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()]
)
logger = logging.getLogger("DesktopAgentUI")

class RedirectText:
    """Redirect print statements to the Tkinter text widget."""
    def __init__(self, text_widget):
        self.output = text_widget

    def write(self, string):
        self.output.configure(state='normal')
        self.output.insert(tk.END, string)
        self.output.see(tk.END)
        self.output.configure(state='disabled')

    def flush(self):
        pass

class DesktopAgentUI:
    """UI for interacting with the autonomous desktop agent."""
    
    def __init__(self, root):
        """Initialize the UI components."""
        self.root = root
        self.root.title("Autonomous Desktop Agent")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Initialize agent in a separate thread to avoid UI freezing
        self.agent = None
        self.interpreter = None
        self.task_thread = None
        self.is_running = False
        
        # Create UI components
        self._create_ui()
        
        # Redirect stdout to text widget
        self.console_redirect = RedirectText(self.console_text)
        sys.stdout = self.console_redirect
        
        # Initialize agent (in separate thread to avoid blocking UI)
        threading.Thread(target=self._initialize_agent).start()
    
    def _create_ui(self):
        """Create the UI components."""
        # Main frame with padding
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = tk.Label(
            main_frame, 
            text="Autonomous Desktop Agent", 
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Task input section
        task_frame = tk.LabelFrame(main_frame, text="Task Input", padx=5, pady=5)
        task_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.task_entry = tk.Entry(task_frame, font=("Helvetica", 12))
        self.task_entry.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.task_entry.bind("<Return>", self._on_submit)
        
        # Console output section
        console_frame = tk.LabelFrame(main_frame, text="Agent Console", padx=5, pady=5)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.console_text = scrolledtext.ScrolledText(
            console_frame, 
            wrap=tk.WORD, 
            font=("Courier", 10),
            bg="#000", 
            fg="#33ff33"
        )
        self.console_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console_text.configure(state='disabled')
        
        # Bottom buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.run_button = tk.Button(
            button_frame, 
            text="Run Task", 
            command=self._run_task,
            bg="#4CAF50", 
            fg="white", 
            font=("Helvetica", 12),
            padx=10
        )
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(
            button_frame, 
            text="Stop Task", 
            command=self._stop_task,
            bg="#F44336", 
            fg="white", 
            font=("Helvetica", 12),
            state=tk.DISABLED,
            padx=10
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(
            button_frame, 
            text="Clear Console", 
            command=self._clear_console,
            font=("Helvetica", 12),
            padx=10
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Initializing agent...")
        status_bar = tk.Label(
            self.root, 
            textvariable=self.status_var, 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _initialize_agent(self):
        """Initialize the desktop agent."""
        try:
            # Display a message in the console
            print("Initializing desktop agent...")
            print("This may take a few seconds...")
            
            # Initialize the agent
            self.agent = DesktopAgent()
            self.interpreter = TaskInterpreter(self.agent)
            
            # Store the interpreter in the agent for direct task matching
            self.agent.interpreter = self.interpreter
            
            # Update the status
            self.status_var.set("Agent ready")
            print("Agent initialization complete!")
            print("Enter a task and click 'Run Task' to begin.")
            
            # Enable the run button
            self.run_button.config(state=tk.NORMAL)
            
        except Exception as e:
            error_msg = f"Error initializing agent: {str(e)}"
            self.status_var.set(error_msg)
            print(error_msg)
            messagebox.showerror("Initialization Error", error_msg)
    
    def _on_submit(self, event=None):
        """Handle task submission via Enter key."""
        self._run_task()
    
    def _run_task(self):
        """Run the task specified in the entry field."""
        if self.is_running:
            messagebox.showinfo("Task In Progress", "A task is already running.")
            return
        
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showinfo("No Task", "Please enter a task to run.")
            return
        
        if not self.agent:
            messagebox.showinfo("Agent Not Ready", "The agent is still initializing.")
            return
        
        # Clear previous task output
        self._clear_console()
        
        # Update UI
        self.is_running = True
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set(f"Running task: {task}")
        
        # Run the task in a separate thread
        self.task_thread = threading.Thread(target=self._execute_task, args=(task,))
        self.task_thread.daemon = True
        self.task_thread.start()
    
    def _execute_task(self, task):
        """Execute the task in a separate thread."""
        try:
            print(f"Starting task: {task}")
            
            # Plan the task
            print("Planning task steps...")
            steps = self.agent.plan_task(task)
            print(f"Task broken down into {len(steps)} steps:")
            for i, step in enumerate(steps):
                print(f"{i+1}. {step}")
            
            # Execute each step
            print("\nExecuting task...")
            for i, step in enumerate(steps):
                if not self.is_running:
                    print("Task execution stopped by user.")
                    break
                
                print(f"\nStep {i+1}/{len(steps)}: {step}")
                self.status_var.set(f"Executing step {i+1}/{len(steps)}")
                
                # Give the user a moment to read the step
                time.sleep(1)
                
                # Execute the step
                success = self.interpreter.interpret_step(step)
                
                if not success:
                    print(f"Failed to execute step: {step}")
                    if messagebox.askyesno("Step Failed", f"Step {i+1} failed. Continue with next step?"):
                        continue
                    else:
                        break
            
            if self.is_running:
                print("\nTask execution completed!")
                self.status_var.set("Task completed")
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            print(error_msg)
            self.status_var.set("Task failed")
            logger.exception("Task execution error")
        
        # Reset UI state
        self.root.after(0, self._reset_ui_after_task)
    
    def _reset_ui_after_task(self):
        """Reset the UI after task completion."""
        self.is_running = False
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def _stop_task(self):
        """Stop the currently running task."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.status_var.set("Stopping task...")
        print("\nStopping task...")
    
    def _clear_console(self):
        """Clear the console output."""
        self.console_text.configure(state='normal')
        self.console_text.delete(1.0, tk.END)
        self.console_text.configure(state='disabled')

if __name__ == "__main__":
    # Create the Tkinter window
    root = tk.Tk()
    app = DesktopAgentUI(root)
    
    # Run the application
    root.mainloop() 