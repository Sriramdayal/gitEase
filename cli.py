import os
import subprocess
import sys

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

# --- Core Functions ---

def run_command(command, show_output=True):
    """Runs a shell command and handles output and errors."""
    print_command(command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        if show_output and result.stdout:
            print(result.stdout)
        return result.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with error:")
        for line in e.stderr.strip().split('\n'):
            print_error(f"  {line}")
        return None, e.stderr

def check_git_installed():
    """Check if Git is installed on the system."""
    _, error = run_command("git --version", show_output=False)
    if error is not None:
        print_error("Git is not installed or not in your PATH.")
        print_info("Please install Git to use this tool: https://git-scm.com/downloads")
        sys.exit(1)

def check_git_config():
    """Check if git user.name and user.email are set and prompts to set them if not."""
    print_header("Checking Git Configuration")
    name, _ = run_command("git config user.name", show_output=False)
    email, _ = run_command("git config user.email", show_output=False)

    if not name or not email:
        print_warning("Git user name and/or email are not set.")
        print_info("These are required to make commits.")
        
        if input("Do you want to set them now (globally)? (y/n): ").lower() == 'y':
            new_name = input("Enter your name: ").strip()
            new_email = input("Enter your email: ").strip()
            if new_name and new_email:
                run_command(f'git config --global user.name "{new_name}"')
                run_command(f'git config --global user.email "{new_email}"')
                print_success("Git user.name and user.email have been set globally.")
            else:
                print_error("Name and email cannot be empty. Please try again.")
    else:
        print_success(f"Git configured for {name} <{email}>")


def is_git_repo():
    """Check if the current directory is a Git repository."""
    return os.path.exists(os.path.join(os.getcwd(), '.git'))

# --- Menu Actions ---

def initialize_repo():
    print_header("1. Initialize Repository")
    if is_git_repo():
        print_info("This directory is already a Git repository.")
        return
    if input("Initialize a new Git repository here? (y/n): ").lower() == 'y':
        run_command("git init -b main")
        print_success("Initialized empty Git repository with default branch 'main'.")
    else:
        print_info("Initialization cancelled.")

def set_remote():
    print_header("2. Set Remote URL")
    if not is_git_repo():
        print_error("Not a Git repository. Please initialize first."); return
    remote_url = input("Enter the remote repository URL: ").strip()
    if not remote_url:
        print_error("URL cannot be empty."); return
    remotes, _ = run_command("git remote", show_output=False)
    if remotes and "origin" in remotes.split('\n'):
        run_command(f"git remote set-url origin {remote_url}")
    else:
        run_command(f"git remote add origin {remote_url}")
    print_success(f"Remote 'origin' has been set to: {remote_url}")

def add_and_commit():
    print_header("3. Add & Commit All Changes")
    if not is_git_repo():
        print_error("Not a Git repository. Please initialize first."); return
    status, _ = run_command("git status --porcelain", show_output=False)
    if not status:
        print_info("No changes to commit. Working directory is clean."); return
    print_info("Current changes:"); run_command("git status -s")
    if input("Stage all the above changes? (y/n): ").lower() != 'y':
        print_info("Staging cancelled."); return
    run_command("git add .")
    print_success("All changes staged.")
    commit_message = input("Enter your commit message: ").strip()
    if not commit_message:
        print_error("Commit message cannot be empty. Aborting."); return
    run_command(f'git commit -m "{commit_message}"')
    print_success("Changes committed.")

def push_to_remote():
    print_header("4. Push to Remote")
    if not is_git_repo(): print_error("Not a Git repository."); return
    _, err = run_command("git rev-parse HEAD", show_output=False)
    if err: print_error("No commits found. Please commit before pushing."); return
    
    local_branch, _ = run_command("git rev-parse --abbrev-ref HEAD", show_output=False)
    if not local_branch: local_branch = "main"

    remote_branch = input(f"Enter remote branch name [{local_branch}]: ").strip() or local_branch
    
    print_info(f"This will push local '{local_branch}' to remote 'origin/{remote_branch}'.")
    if input("Continue? (y/n): ").lower() == 'y':
        run_command(f"git push origin {local_branch}:{remote_branch}")
        print_success("Push completed.")
    else:
        print_info("Push cancelled.")

def pull_from_remote():
    print_header("5. Pull from Remote")
    if not is_git_repo(): print_error("Not a Git repository."); return
    local_branch, _ = run_command("git rev-parse --abbrev-ref HEAD", show_output=False)
    if not local_branch: print_error("Could not determine local branch."); return
    remote_branch = input(f"Enter remote branch to pull from [{local_branch}]: ").strip() or local_branch
    print_info(f"Pulling from 'origin/{remote_branch}' and merging into local '{local_branch}'.")
    if input("Continue? (y/n): ").lower() == 'y':
        run_command(f"git pull origin {remote_branch}")
        print_success("Pull completed.")
    else:
        print_info("Pull cancelled.")

def branch_management():
    print_header("6. Branch Management")
    if not is_git_repo(): print_error("Not a Git repository."); return
    
    while True:
        print("\n  Branch Menu:")
        print("    a. List Branches (local & remote)")
        print("    b. Create New Branch")
        print("    c. Switch Branch (checkout)")
        print("    d. Delete Local Branch")
        print("    e. Return to Main Menu")
        choice = input("  Select an option: ").lower()

        if choice == 'a':
            print_info("Listing all branches:")
            run_command("git branch -a")
        elif choice == 'b':
            new_branch = input("Enter new branch name: ").strip()
            if new_branch: run_command(f"git branch {new_branch}")
            else: print_error("Branch name cannot be empty.")
        elif choice == 'c':
            branch_to_switch = input("Enter branch name to switch to: ").strip()
            if branch_to_switch: run_command(f"git checkout {branch_to_switch}")
            else: print_error("Branch name cannot be empty.")
        elif choice == 'd':
            branch_to_delete = input("Enter local branch name to delete: ").strip()
            if branch_to_delete:
                if input(f"{BColors.WARNING}Are you sure you want to delete '{branch_to_delete}'? This cannot be undone. (y/n): {BColors.ENDC}").lower() == 'y':
                    run_command(f"git branch -d {branch_to_delete}")
            else: print_error("Branch name cannot be empty.")
        elif choice == 'e':
            break
        else:
            print_error("Invalid choice.")

def show_status():
    print_header("7. Show Status")
    if not is_git_repo(): print_error("Not a Git repository."); return
    run_command("git status")

def view_commit_history():
    print_header("8. View Commit History")
    if not is_git_repo(): print_error("Not a Git repository."); return
    run_command("git log --graph --oneline --decorate --all")

# --- Main Application Loop ---
def main():
    check_git_installed()
    check_git_config()
    input("\nConfiguration check complete. Press Enter to continue to the main menu...")

    while True:
        print_header("GitEase CLI - Main Menu")
        print(f"Directory: {BColors.OKBLUE}{os.getcwd()}{BColors.ENDC}")
        if is_git_repo():
            print(f"{BColors.OKGREEN}✓ Git repository detected.{BColors.ENDC}")
            try:
                remote_url = subprocess.check_output("git remote get-url origin", shell=True, text=True, stderr=subprocess.DEVNULL).strip()
                print(f"  Remote URL: {BColors.OKCYAN}{remote_url}{BColors.ENDC}")
            except subprocess.CalledProcessError:
                print(f"{BColors.WARNING}i Remote 'origin' not set.{BColors.ENDC}")
        else:
            print(f"{BColors.WARNING}✗ No Git repository detected.{BColors.ENDC}")

        print("\nWhat would you like to do?")
        print("  1. Initialize Repo             5. Pull from Remote")
        print("  2. Set Remote URL              6. Branch Management")
        print("  3. Add & Commit All Changes    7. Show Status")
        print("  4. Push to Remote              8. View Commit History")
        print("  9. Exit")
        
        choice = input("\nEnter your choice (1-9): ")
        
        actions = {
            '1': initialize_repo, '2': set_remote, '3': add_and_commit,
            '4': push_to_remote, '5': pull_from_remote, '6': branch_management,
            '7': show_status, '8': view_commit_history
        }

        if choice in actions:
            actions[choice]()
        elif choice == '9':
            print_info("Exiting GitEase CLI. Goodbye!"); break
        else:
            print_error("Invalid choice. Please enter a number between 1 and 9.")
        
        if choice != '9':
            input("\nPress Enter to return to the menu...")

if __name__ == "__main__":
    main()

