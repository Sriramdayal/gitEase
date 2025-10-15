import os
import subprocess
import sys
import yaml
import re

# --- ANSI Color Codes for better terminal output ---
class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# --- Helper Print Functions ---
def print_header(message):
    print(f"\n{BColors.HEADER}{BColors.BOLD}--- {message} ---{BColors.ENDC}")

def print_success(message):
    print(f"{BColors.OKGREEN}✓ {message}{BColors.ENDC}")

def print_error(message):
    print(f"{BColors.FAIL}✗ {message}{BColors.ENDC}")

def print_info(message):
    print(f"{BColors.OKCYAN}i {message}{BColors.ENDC}")

def print_command(command):
    print(f"{BColors.WARNING}$ {command}{BColors.ENDC}")

# --- Core Agent Functions ---

def run_command(command, show_output=True):
    """Runs a shell command and returns True on success, False on failure."""
    print_command(command)
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        if show_output:
            for line in process.stdout:
                print(line, end='')
        
        process.wait() # Wait for the command to complete
        
        if process.returncode != 0:
            for line in process.stderr:
                print_error(f"  {line.strip()}")
            return False
        return True
    except Exception as e:
        print_error(f"An exception occurred: {e}")
        return False

def load_config():
    """Loads the workflow.yml configuration file."""
    config_path = os.path.join(os.getcwd(), '.gitease', 'workflow.yml')
    if not os.path.exists(config_path):
        print_error("Configuration file not found!")
        print_info(f"Please create a '.gitease/workflow.yml' file in your project root.")
        return None
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print_error(f"Error parsing YAML file: {e}")
        return None

def get_current_branch():
    """Gets the current active Git branch."""
    try:
        result = subprocess.check_output(
            "git rev-parse --abbrev-ref HEAD", 
            shell=True, text=True
        ).strip()
        return result
    except subprocess.CalledProcessError:
        print_error("Could not determine current Git branch. Are you in a Git repository?")
        return None

def substitute_variables(command_string, config):
    """Substitutes placeholders like {{branches.development}} in a command string."""
    placeholders = re.findall(r"\{\{(.*?)\}\}", command_string)
    for placeholder in placeholders:
        keys = placeholder.strip().split('.')
        value = config
        try:
            for key in keys:
                value = value[key]
            command_string = command_string.replace(f"{{{{{placeholder}}}}}", value)
        except KeyError:
            # Handle dynamic variables that need user input
            if placeholder == 'version':
                version_input = input(f"Please enter the version for the tag (e.g., 1.2.3): ").strip()
                if not version_input:
                    print_error("Version cannot be empty.")
                    return None
                command_string = command_string.replace("{{version}}", version_input)
            else:
                print_error(f"Variable '{placeholder}' not found in config.")
                return None
    return command_string


def execute_workflow(workflow_name, config, current_branch):
    """Executes all steps for a given workflow after user confirmation."""
    workflow = config.get('workflows', {}).get(workflow_name)
    if not workflow:
        print_error(f"Workflow '{workflow_name}' not found in your config file.")
        return

    print_header(f"Workflow Plan: '{workflow_name}'")
    
    # --- Dry Run Phase ---
    plan = []
    for step in workflow:
        description = step.get('description', 'No description')
        run_cmd = step.get('run', '')
        
        # Substitute variables for the plan
        planned_cmd = substitute_variables(run_cmd, config)
        if planned_cmd is None: return # Error during substitution
        
        plan.append({'description': description, 'command': planned_cmd})
        
    print_info("The agent will perform the following steps:")
    for i, step_plan in enumerate(plan, 1):
        print(f"  {i}. {step_plan['description']}")
        print(f"     {BColors.WARNING}↳ {step_plan['command']}{BColors.ENDC}")
        
    if input("\nDo you want to proceed with execution? (y/n): ").lower() != 'y':
        print_info("Execution cancelled by user.")
        return

    # --- Execution Phase ---
    print_header(f"Executing Workflow: '{workflow_name}'")
    for i, step_plan in enumerate(plan, 1):
        print(f"\n--- Step {i}/{len(plan)}: {step_plan['description']} ---")
        
        command = step_plan['command']
        success = True
        
        if command.startswith("hooks:"):
            hook_name = command.split(':')[1].strip()
            hook_commands = config.get('hooks', {}).get(hook_name, [])
            for hook_cmd in hook_commands:
                if not run_command(hook_cmd):
                    success = False
                    break
        elif command.startswith("git merge_to_branch:"):
            target_branch = command.split(':')[1].strip()
            print_info(f"Performing safe merge from '{current_branch}' to '{target_branch}'...")
            success = (
                run_command(f"git checkout {target_branch}") and
                run_command(f"git pull origin {target_branch}") and
                run_command(f"git merge {current_branch}") and
                run_command(f"git checkout {current_branch}") # Switch back
            )
        else:
            success = run_command(command)
        
        if not success:
            print_error(f"Step failed. Aborting workflow.")
            break
        else:
            print_success("Step completed successfully.")
    
    print_header("Workflow finished.")


def main():
    """Main function to run the GitEase Agent CLI."""
    config = load_config()
    if not config:
        sys.exit(1)

    current_branch = get_current_branch()
    if not current_branch:
        sys.exit(1)
        
    project_name = config.get('project_name', 'Unnamed Project')
    print_header(f"GitEase Agent for '{project_name}'")
    print(f"Current Branch: {BColors.OKBLUE}{current_branch}{BColors.ENDC}")

    available_workflows = list(config.get('workflows', {}).keys())
    if not available_workflows:
        print_error("No workflows defined in your '.gitease/workflow.yml' file.")
        sys.exit(1)

    print("\nAvailable Workflows:")
    for i, name in enumerate(available_workflows, 1):
        print(f"  {i}. {name}")

    try:
        choice_str = input("\nEnter the number of the workflow to run: ")
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(available_workflows):
            selected_workflow = available_workflows[choice_index]
            execute_workflow(selected_workflow, config, current_branch)
        else:
            print_error("Invalid choice.")
    except (ValueError, IndexError):
        print_error("Invalid input. Please enter a number from the list.")
    except KeyboardInterrupt:
        print_info("\nOperation cancelled by user. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
