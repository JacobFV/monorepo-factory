import shutil
from textwrap import dedent
from typing import final
import typer
from rich.console import Console
from rich.tree import Tree
from box import Box
from subprocess import check_output, CalledProcessError
import os
import networkx as nx
import fnmatch


app = typer.Typer()
console = Console()


def sh(cmd: str, cwd: str = None):
    try:
        return check_output(cmd, shell=True, cwd=cwd, text=True)
    except CalledProcessError as e:
        console.print(f"An error occurred while executing the command: {cmd}")
        console.print(f"Error details: {e.output}")
        raise


def sort_patterns(patterns):
    # Sort patterns by their specificity (length in this case)
    return sorted(patterns, key=lambda p: len(p["pattern"]), reverse=True)


def apply_defaults_to_repo(repo, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(repo.name, pattern.get("pattern", "*")):
            for key, value in pattern.items():
                if key != "pattern":
                    repo.setdefault(key, value)
    return repo


def build_dependency_graph(repos):
    graph = nx.DiGraph()

    # Iterate through each repo and subrepo to build the graph
    for repo in repos:
        # Add each top-level repo as a node
        graph.add_node(repo.name)

        # If the repo has a clone source, add an edge from the clone source to the repo
        # This indicates that the repo depends on its clone source
        if "clone" in repo:
            graph.add_edge(repo.clone, repo.name)

        # Process subrepos if any
        if "subrepos" in repo:
            for subrepo in repo.subrepos:
                # Add each subrepo as a node
                graph.add_node(subrepo.name)

                # If the subrepo has a clone source, add an edge from the clone source to the subrepo
                # This ensures the subrepo is created before being added as a submodule
                if "clone" in subrepo:
                    graph.add_edge(subrepo.clone, subrepo.name)

                # Create a dependency from the parent repo to its subrepo
                # This ensures that the subrepos are processed before its parent
                graph.add_edge(subrepo.name, repo.name)

    return graph


def create_or_update_repo(repos, repo, base_path):
    org_name = None
    match repo.name.split("/"):
        case [org_name, repo_name]:
            org_path = os.path.join(base_path, org_name)
            repo_path = os.path.join(org_path, repo_name)
            if not os.path.exists(org_path):
                os.makedirs(org_path, exist_ok=True)
        case [repo_name]:
            repo_path = os.path.join(base_path, repo_name)
        case _:
            raise ValueError(f"Invalid repository name: {repo.name}")

    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)

    if "clone" in repo:
        sh(f"git clone {repo.clone} {repo_path}")
    else:
        os.makedirs(repo_path, exist_ok=True)
        sh(f"git init", cwd=repo_path)
    with open(os.path.join(repo_path, "README.md"), "w") as readme:
        readme.write(f"# {repo.name}")
        if "description" in repo:
            readme.write(f"\n\n{repo.description}")
    sh(f"git add .", cwd=repo_path)
    sh(f"git commit -m 'initial commit'", cwd=repo_path)

    currently_created_branches = set()
    if "submodules" in repo:
        for subrepo_entry in repo.subrepos:
            suprepo_name = subrepo_entry.name
            subrepo = next(
                (r for r in repos if r.name == repo_name), None
            )  # TODO: get by dict lookup
            if (
                "branches" in repo
                and "branches" in subrepo
                and repo.branches
                and subrepo.branches
            ):
                # add submodule for each branch that matches
                for branch in repo.branches:
                    sh(f"git checkout -b {branch}", cwd=repo_path)
            else:
                # just use the subrepo default branch
                match subrepo.name.split("/"):
                    case [org_name, subrepo_dirname]:
                        relative_subrepo_path = f"../{subrepo_dirname}"
                    case [subrepo_org_name, subrepo_dirname]:
                        relative_subrepo_path = (
                            f"../../{subrepo_org_name}/{subrepo_dirname}"
                        )
                    case [subrepo_dirname]:
                        relative_subrepo_path = f"../{subrepo_dirname}"
                    case _:
                        raise Exception(f"Invalid format: {subrepo.name}")

                sh(
                    f"git submodule add {relative_subrepo_path}.git {subrepo.path}",
                    cwd=repo_path,
                )

    if "branches" in repo:
        for branch in set(repo.branches) - currently_created_branches:
            sh(f"git checkout -b {branch}", cwd=repo_path)
        sh(f"git checkout main", cwd=repo_path)


def extract_subrepos(repos):
    final_repos = []
    for repo in repos:
        if "subrepo" in repo:
            for subrepo in repo.subrepos:
                final_repos.append({"name": subrepo.name})
        final_repos.append(repo)

    repos, final_repos = final_repos, []

    for repo in repos:
        for final_repo in final_repos:
            if final_repo.name == repo.name:
                final_repo.update(repo)
        else:
            final_repos.append(repo)

    return final_repos


@app.command()
def generate(file: str):
    file_path = os.path.abspath(file)
    base_path = os.path.dirname(file_path)

    data = Box.from_toml(filename=file)
    repos = extract_subrepos(repos)
    pattern_definitions = [repo for repo in data.repo if "pattern" in repo]
    sorted_patterns = sort_patterns(pattern_definitions)
    repos = [
        apply_defaults_to_repo(repo, sorted_patterns)
        for repo in data.repo
        if "name" in repo
    ]
    graph = build_dependency_graph(repos)

    os.chdir(base_path)

    for repo_name in nx.topological_sort(graph):
        repo = next((r for r in repos if r.name == repo_name), None)
        if repo:
            create_or_update_repo(repos, repo, base_path)

    # Displaying the tree (optional, for visualization)
    tree = Tree("🌌 Repositories")
    for repo in repos:
        repo_node = tree.add(
            f"[bold green]{repo.name}[/bold green]: {repo.description.strip()}"
        )
        if "branches" in repo:
            branches_node = repo_node.add("[bold yellow]Branches[/bold yellow]")
            for branch in repo.branches:
                branches_node.add(branch)
        if "subrepos" in repo:
            subrepos_node = repo_node.add("[bold blue]Subrepos[/bold blue]")
            for subrepo in repo.subrepos:
                subrepos_node.add(f"{subrepo.path} - {subrepo.name}")
    console.print(tree)


if __name__ == "__main__":
    app()
