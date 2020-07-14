import csv
from functools import partial
from itertools import chain

import click
from graphviz import Digraph

from gwf.core import Graph, Scheduler, TargetStatus
from gwf.filtering import filter_names
from gwf.exceptions import GWFError
from gwf.backends import Backend


def dfs(graph, root, visited={}):
    path = []

    def dfs_inner(node):
        if node in visited:
            return
        visited.add(node)
        for dep in graph.dependencies[node]:
            dfs_inner(dep)
        path.append(node)

    dfs_inner(root)
    return path


def visit_all_dependencies(graph, matches):
    visited = set()
    paths = map(partial(dfs, graph, visited=visited), matches)
    for target in chain(*paths):
        yield target


def get_targets_status(obj, graph, matches):
    status_dict = dict()
    backend_cls = Backend.from_config(obj)
    with backend_cls() as backend:
        scheduler = Scheduler(graph, backend)
        for target in visit_all_dependencies(graph, matches):
            status_dict[target] = scheduler.status(target)
    return status_dict


status_colors = {
    TargetStatus.SHOULDRUN: "purple",
    TargetStatus.SUBMITTED: "yellow",
    TargetStatus.RUNNING: "blue",
    TargetStatus.COMPLETED: "green",
}


@click.command()
@click.argument("targets", nargs=-1)
@click.option(
    "--output-type", type=click.Choice(["graphviz", "cytoscape"]), default="graphviz"
)
@click.option("--status/--no-status", default=False)
@click.pass_obj
def graph(obj, targets, output_type, status):
    graph = Graph.from_config(obj)

    # If targets supplyed only show dependencies for thoes targets
    # otherwise show the whole workflow
    matches = graph.targets.values()
    if targets:
        matches = filter_names(matches, targets)
        # Prevent drawing an empty graph
        if not matches:
            raise GWFError("Non of the targets was found in the workflow")
    if status:
        status_dict = get_targets_status(obj, graph, matches)

    if output_type == "graphviz":
        dot = Digraph(
            comment="Dependency Graph",
            graph_attr={"splines": "curved"},
            node_attr={"style": "filled"},
            edge_attr={"arrowsize": ".5"},
        )
        for target in visit_all_dependencies(graph, matches):
            name = target.name
            color = "white"
            if status:
                color = status_colors[status_dict[target]]
            dot.node(name, name, fillcolor=color)  # shape='parallelogram'
            for dep_target in graph.dependencies[target]:
                dot.edge(name, dep_target.name)
        dot.render("dependency_graph.gv")
    elif output_type == "cytoscape":
        with open("dependency_graph.sif", "w") as fp:
            writer = csv.writer(fp, delimiter=" ")
            for target in visit_all_dependencies(graph, matches):
                name = target.name
                dependencies = list(map(lambda d: d.name, graph.dependencies[target]))
                if dependencies:
                    writer.writerow([name, "dependencies"] + dependencies)
