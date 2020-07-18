import sys
import csv
from functools import partial
from itertools import chain
from collections import defaultdict

import click
import graphviz
from graphviz import Digraph
import attr

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


def bfs(graph, root, visited={}):
    queue = [root]
    path = []

    while queue:
        node = queue.pop(0)
        if node not in visited:
            visited.add(node)
            for dep in graph.dependencies[node]:
                queue.append()
            path.append(node)
    return path


def visit_all_dependencies(func, graph, matches):
    visited = set()
    paths = map(partial(func, graph, visited=visited), matches)
    for target in chain(*paths):
        yield target


def visit_all_dependencies_bfs(graph, matches):
    yield from visit_all_dependencies(bfs, graph, matches)


def visit_all_dependencies_dfs(graph, matches):
    yield from visit_all_dependencies(dfs, graph, matches)


def get_targets_status(obj, graph, matches):
    status_dict = dict()
    backend_cls = Backend.from_config(obj)
    with backend_cls() as backend:
        scheduler = Scheduler(graph, backend)
        for target in visit_all_dependencies_dfs(graph, matches):
            status_dict[target] = scheduler.status(target)
    return status_dict


status_colors = {
    TargetStatus.SHOULDRUN: "purple",
    TargetStatus.SUBMITTED: "yellow",
    TargetStatus.RUNNING: "blue",
    TargetStatus.COMPLETED: "green",
}


def sif_format(graph, matches, conf):
    lines = list()
    for target in visit_all_dependencies_dfs(graph, matches):
        name = target.name
        dependencies = list(map(lambda d: d.name, graph.dependencies[target]))
        if dependencies:
            lines.append(
                "{} {} {}".format(name, "dependencies", " ".join(dependencies))
            )
    return "\n".join(lines)


def more_than_n_children(graph, n, target):
    return len(graph.dependencies[target]) > n


def have_multiple_children(graph, target):
    return more_than_n_children(graph, target, 1)


def follow_simple_path(graph, init):
    path = list()

    def dfs_inner(node):
        if have_multiple_children(node):
            return
        for dep in graph.dependencies[node]:
            dfs_inner(dep)
        path.append(node)

    dfs_inner(root)
    return path


# TODO: This function is not finished
def fint_parallel_paths(graph, matches):
    candidats = dict()
    spitting_targets = filter(
        partial(have_many_children, graph, 4),
        visit_all_dependencies_bfs(graph, matches),
    )
    for target in spitting_targets:
        candidats[target] = [
            follow_simple_path(dep) for dep in graph.dependencies[target]
        ]
    pass


def create_dot_graph(graph, matches, conf):
    dot = Digraph(
        comment="Dependency Graph",
        graph_attr={"splines": "curved"},
        node_attr={"style": "filled"},
        edge_attr={"arrowsize": ".5"},
    )
    for target in visit_all_dependencies_dfs(graph, matches):
        name = target.name
        color = "white"
        if conf.status_dict != None:
            color = status_colors[conf.status_dict[target]]
        dot.node(name, name, fillcolor=color)  # shape='parallelogram'
        for dep_target in graph.dependencies[target]:
            dot.edge(name, dep_target.name)
    return dot


def dot_format(graph, matches, conf):
    dot = create_dot_graph(graph, matches, conf)
    return dot.source


def graphviz_formats(graph, matches, conf):
    dot = create_dot_graph(graph, matches, conf)
    output_file = "dependency_graph.gv"
    if conf.output != sys.stdout:
        output_file = conf.output
    dot.render(output_file, format=conf.format)


@attr.s
class Configurations(object):
    func = attr.ib()
    format = attr.ib(default=None)
    output = attr.ib(default=sys.stdout)
    status_dict = attr.ib(default=None)
    compact = attr.ib(default=False)


def default_conf():
    return Configurations(func=graphviz_formats)


format_conf = defaultdict(
    default_conf,
    {"sif": Configurations(func=sif_format), "dot": Configurations(func=dot_format),},
)
FORMATS = set(format_conf.keys()) | graphviz.backend.FORMATS


def output_result(conf, output_str):
    if not output_str:
        return
    if conf.output == sys.stdout:
        print(output_str)
    else:
        with open(conf.output, "w") as fp:
            fp.write(output_str)


@click.command()
@click.argument("targets", nargs=-1)
@click.option("-f", "--output-format", type=click.Choice(FORMATS), default="svg")
@click.option("-o", "--output", default=None)
@click.option("--status/--no-status", default=False)
@click.option("--compact/--no-compact", default=False)
@click.pass_obj
def graph(obj, targets, output_format, output, status, compact):
    graph = Graph.from_config(obj)

    # If targets supplyed only show dependencies for thoes targets
    # otherwise show the whole workflow
    matches = graph.targets.values()
    if targets:
        matches = filter_names(matches, targets)
        # Prevent drawing an empty graph
        if not matches:
            raise GWFError("Non of the targets was found in the workflow")

    conf = format_conf[output_format]
    conf.format = output_format  # necessary for defaulting to graphviz formats

    if status:
        conf.status_dict = get_targets_status(obj, graph, matches)
    if output:
        conf.output = output
    if compact:
        conf.compact = compact

    output_str = conf.func(graph, matches, conf)
    output_result(conf, output_str)
