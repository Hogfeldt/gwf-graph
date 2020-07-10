import click
from graphviz import Digraph

from gwf.core import Graph
from gwf.filtering import filter_names

@click.command()
@click.argument('targets', nargs=-1)
@click.pass_obj
def graph(obj, targets):
    graph = Graph.from_config(obj)

    matches = graph.targets.values()
    if targets:
        matches = filter_names(matches, targets)

    dot = Digraph(comment='Dependency Graph')
    visited = set()
    for root in matches:
        if root in visited:
            continue
        for target in graph.dfs(root):
            name = target.name
            if name in visited:
                continue
            dot.node(name, name)    #shape='parallelogram'
            for dep_target in graph.dependencies[target]:
                dot.edge(name, dep_target.name)
            visited.add(name)
    dot.render('dependency_graph.gv')
