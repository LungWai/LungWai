import subprocess
import json
import sys

def check_gh_cli():
    """Checks if the GitHub CLI is installed."""
    try:
        # Run 'gh --version' and suppress its output.
        subprocess.run(
            "gh --version",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: GitHub CLI ('gh') is not installed or not in your PATH.")
        print("Please install it from: https://cli.github.com/")
        return False

def main():
    """
    Main function to authenticate with GitHub CLI and fetch all repository URLs.
    """
    if not check_gh_cli():
        sys.exit(1)

    print("Step 1: Checking GitHub CLI authentication status...")
    try:
        # First, check if we are already logged in to avoid unnecessary browser popups.
        subprocess.run(
            "gh auth status",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Already logged in.")
    except subprocess.CalledProcessError:
        print("-> You are not logged in. Please follow the prompts to authenticate.")
        print("-> Your browser may open for you to complete the login process.")
        # The 'gh auth login' command is interactive. We run it and let the user
        # interact with it directly in their terminal.
        # We don't capture output here because it's an interactive process.
        auth_process = subprocess.run("gh auth login", shell=True)
        if auth_process.returncode != 0:
            print("\n❌ Authentication failed. Please try running the script again.")
            sys.exit(1)
        print("\n✅ Authentication successful!")


    print("\nStep 2: Fetching all your repository links...")
    try:
        # Fetch all repos (up to 1000) in JSON format, getting only the name and URL.
        # The 'gh' command is run, and its output is captured.
        result = subprocess.run(
            'gh repo list --limit 1000 --json name,url',
            shell=True,
            check=True,        # This will raise an exception if the command fails
            capture_output=True, # Capture stdout and stderr
            text=True          # Decode stdout/stderr as text
        )

        # The output from the command is a JSON string, so we parse it.
        repos = json.loads(result.stdout)

        if not repos:
            print("No repositories found for your account.")
            return

        print(f"\n✅ Success! Found {len(repos)} repositories. Here are the links:\n")

        # Print each repository URL on a new line.
        for repo in repos:
            print(repo['url'])

    except subprocess.CalledProcessError as e:
        print("\n❌ An error occurred while fetching repositories.")
        print(f"Error details: {e.stderr}")
    except json.JSONDecodeError:
        print("\n❌ Could not parse the repository list from the GitHub CLI.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
