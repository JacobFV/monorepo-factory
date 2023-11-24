from pathlib import Path
import subprocess
from time import sleep
import yaml
import os
import typer
from rich.console import Console
from typing import List, Dict, Optional

# Initialize Typer and Rich Console
app = typer.Typer(
    help="This application automates the creation and setup of GitHub repositories based on a YAML configuration file. It supports creating root repositories and their forks, with options to specify the organization and visibility (public/private)."
)
console = Console()


def run_command(
    command: List[str], cwd: Optional[str] = None, capture_output: bool = False
) -> Optional[str]:
    """Run a shell command using subprocess."""
    try:
        print(f'{cwd} $ {" ".join(command)}')
        result = subprocess.check_output(command, cwd=cwd, text=True)
        if capture_output:
            return result.strip()
        return None
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error executing {' '.join(command)}: {e.output}[/red]")
        if capture_output:
            return None
        raise


def extract_org_repo(name: str) -> tuple[str, str]:
    """Extract organization and repo name from the given string."""
    parts = name.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", parts[0]


@app.command()
def create_repos(
    file_path: str = typer.Argument(
        ..., help="Path to the YAML file with repo structure"
    ),
    default_visibility: str = typer.Option(
        "public", help="Default visibility for repositories (public/private)"
    ),
    git_dir: str = typer.Option("", help="Directory to create git repositories in"),
):
    """Command to create repositories as per the YAML structure."""
    base_dir = git_dir if git_dir else str(Path(file_path).parent)

    try:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
            for repo_data in data:
                process_repos(
                    repo_data,
                    default_visibility=default_visibility,
                    base_dir=base_dir,
                    create=True,
                )
    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML: {e}[/red]")


@app.command()
def check_repos(
    file_path: str = typer.Argument(
        ..., help="Path to the YAML file with repo structure"
    )
):
    """Command to check the existence of repositories as per the YAML structure."""
    try:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
            for repo_data in data:
                process_repos(repo_data, create=False)
    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML: {e}[/red]")


@app.command()
def mock_repos(
    file_path: str = typer.Argument(
        ..., help="Path to the YAML file with repo structure"
    ),
    git_dir: str = typer.Option("", help="Directory to create git repositories in"),
):
    """Command to mock create the repositories as per the YAML structure."""
    git_dir = git_dir or Path(file_path).parent
    git_dir = Path(git_dir)

    try:
        with open(file_path, "r") as yml_config:
            data = yaml.safe_load(yml_config)
    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
        typer.Exit(1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML: {e}[/red]")
        typer.Exit(1)

    create_mock_repos(git_dir, data)
    typer.Exit(0)

def create_mock_repos(git_dir, data):
    for repo_data in data:
        _, name = extract_org_repo(repo_data["name"])
        run_command(["mkdir", "-p", str(git_dir / repo_data['name'])], cwd=".")
        with open(git_dir / repo_data["name"] / "README.md", "w") as f:
            f.write(f"# {name}\n")
        if "forks" in repo_data:
            create_mock_repos(git_dir, repo_data["forks"])


def process_repos(
    repo_data: Dict,
    parent: Optional[str] = None,
    default_visibility: str = "public",
    base_dir: str = "",
    create: bool = True,
) -> None:
    """Process each repo and its forks recursively for creation or checking existence."""
    full_name = repo_data["name"]
    org, repo_name = extract_org_repo(full_name)

    if create:
        create_repo(org, repo_name, default_visibility, base_dir)
    else:
        check_repo_existence(org, repo_name)

    # Process forks if they exist
    for fork in repo_data.get("forks", []):
        process_repos(fork, full_name, default_visibility, base_dir, create)


def create_repo(org: str, repo_name: str, visibility: str, base_dir: str) -> None:
    """Create local and remote repo, and push it to GitHub."""
    repo_path = os.path.join(base_dir, repo_name)

    # Create local repo
    os.makedirs(repo_path, exist_ok=True)
    run_command(["git", "init"], cwd=repo_path)

    # Create README and make initial commit
    readme_path = os.path.join(repo_path, "README.md")
    with open(readme_path, "w") as file:
        file.write(f"# {repo_name}")
    sleep(0.1)
    run_command(["git", "add", readme_path], cwd=repo_path)
    run_command(["git", "commit", "-m", "Initial commit"], cwd=repo_path)

    # Create remote repo and push
    remote_url = f"{org}/{repo_name}" if org else repo_name
    visibility_flag = "--public" if visibility == "public" else "--private"
    run_command(
        [
            "gh",
            "repo",
            "create",
            remote_url,
            visibility_flag,
            "--source=.",
            "--remote=upstream",
            "--push",
        ],
        cwd=repo_path,
    )


def check_repo_existence(org: str, repo_name: str) -> None:
    """Check if a repository exists."""
    repo_full_name = f"{org}/{repo_name}" if org else repo_name
    result = run_command(["gh", "repo", "view", repo_full_name], capture_output=True)
    if result:
        console.print(f"[green]Repository exists: {repo_full_name}[/green]")
    else:
        console.print(f"[yellow]Repository does not exist: {repo_full_name}[/yellow]")


if __name__ == "__main__":
    app()
