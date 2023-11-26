from contextlib import contextmanager
from functools import reduce
import os
import re
import shutil
import subprocess
from typing import Dict
from box import Box
import networkx as nx
import typer
from pathlib import Path
from rich.console import Console

# Initialize Rich console
console = Console()


@contextmanager
def cwd(path):
    """Context manager for changing the current working directory."""
    original_path = os.getcwd()

    path = Path(path)
    original_path = Path(original_path)

    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    try:
        os.chdir(str(path))
        yield original_path, path
    finally:
        os.chdir(str(original_path))


def sh(cmd: str, cwd: str = None):
    """Execute a shell command in a specific directory and return its output."""
    try:
        return subprocess.check_output(cmd, shell=True, cwd=cwd, text=True)
    except subprocess.CalledProcessError as e:
        console.print(f"An error occurred while executing the command: {cmd}")
        console.print(f"Error details: {e.output}")
        raise


def identify_repos(data: Box) -> Box[str, dict]:
    """Identify all repositories and their contents from the provided data."""
    repos = {repo_data.name: repo_data for repo_data in data.repo}
    for repo_data in data.repo:
        for subrepo in repo_data.get("subrepos", []):
            repos.setdefault(subrepo.name, {}).update({"name": subrepo.name})
    return Box(repos)


def identify_patterns(data: Box) -> Box[str, dict]:
    """Identify all patterns and their contents from the provided data."""
    return {pattern_data.pattern: pattern_data for pattern_data in data.pattern}


def prep_repos(repos: Box[str, dict], patterns: Box[str, dict]):
    # add path
    for repo in repos.values():
        repo["path"] = Path(repo["name"])
        if repo.path.exists():
            shutil.rmtree(str(repo.path))
    # add path to root (handles cases for both ./org/repo and ./userrepo)
    for repo in repos.values():
        repo["path_to_root_from_outside"] = Path("./.." if "/" in repo.name else ".")
        repo["path_to_root_from_inside"] = repo.path_to_root_from_outside / ".."

    # apply patterns to all matching repos
    matching_patterns = {
        repo.name: [
            pattern_data
            for pattern, pattern_data in patterns.items()
            if re.match(pattern, repo.name)
        ]
        for repo in repos.values()
    }
    for repo_name in repos.keys():
        matching_patterns_by_priority = sorted(
            matching_patterns[repo_name],
            key=lambda pattern: len(
                max(re.findall(pattern.pattern, repo_name), key=len, default="")
            ),
        )
        repo_data_overrides = matching_patterns_by_priority + [repos[repo_name]]
        repos[repo_name] = reduce(lambda x, y: {**x, **y}, repo_data_overrides)


def initialize_repo(repo):
    # Initialize with README
    with open("README.md", "w") as file:
        file.write(f"# {repo.name}\n\n{repo.get('description', None)}")
    sh(f"git add .")
    sh(f'git commit -m "Initial commit"')


def build_clone_graph(repos: Dict[str, dict]) -> nx.DiGraph:
    """Build a graph representing the creation order of repositories."""
    graph = nx.DiGraph()
    graph.add_nodes_from(repos.keys())
    for repo in repos.values():
        if "clone" in repo:
            graph.add_edge(repo.clone, repo.name)
    return graph


def create_repo(repo):
    """Create a new repository."""
    repo.path.mkdir(parents=True, exist_ok=True)
    with cwd(repo.path):
        sh(f"git init")
        initialize_repo(repo)


def clone_repo(repo, clone):
    """Clone a repository from a source."""
    with cwd(repo.path.parent):
        clone_relpath = repo.path_to_root_from_outside / clone.path
        sh(f"git clone {clone_relpath} {repo.path.name}")
        with cwd(repo.path.name):
            initialize_repo(repo)


def create_or_clone_repos(repos: Dict[str, dict]):
    """Create or clone repositories based on the provided graph."""
    clone_graph = build_clone_graph(repos)
    for repo_name in nx.topological_sort(clone_graph):
        repo = repos[repo_name]

        if "clone" in repo:
            clone_repo(repo, repos[repo.clone])
        else:
            create_repo(repo)


def build_submodule_graph(repos: Dict[str, dict]) -> nx.DiGraph:
    """Build a graph representing the relationships between repositories and submodules."""
    graph = nx.DiGraph()
    for repo in repos.values():
        for subrepo in repo.get("subrepos", []):
            graph.add_edge(repo.name, subrepo.name)
    return graph


def setup_submodules(repos: Dict[str, dict]):
    """Setup submodules for the repositories based on the provided graph."""
    submodule_graph = build_submodule_graph(repos)
    for repo_name in nx.topological_sort(submodule_graph):
        repo = repos[repo_name]
        if "subrepos" in repo and repo.subrepos:
            with cwd(repo.path):
                for subrepo_name in submodule_graph.successors(repo.name):
                    subrepo_in_repo = next(
                        subrepo
                        for subrepo in repo.subrepos
                        if subrepo.name == subrepo_name
                    )
                    sh(
                        f"git submodule add {repo.path_to_root_from_inside / repos[subrepo_name].path} {subrepo_in_repo.path}"
                    )

                sh("git add .")
                sh('git commit -m "Added submodules"')


def main(toml_file: str):
    """Main function to set up repositories and submodules from a TOML configuration file."""
    data = Box.from_toml(filename=toml_file)
    with cwd(Path(toml_file).parent):
        repos = identify_repos(data)
        patterns = identify_patterns(data)
        prep_repos(repos, patterns)
        create_or_clone_repos(repos)
        setup_submodules(repos)
        console.print("[green]Repository setup completed successfully![/green]")


if __name__ == "__main__":
    typer.run(main)
