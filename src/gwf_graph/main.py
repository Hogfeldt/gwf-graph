import click
from graphviz import Digraph

from gwf.core import Graph
from gwf.filtering import filter_names
from gwf.exceptions import GWFError

first = lambda p: p[0]

@click.command()
@click.argument('targets', nargs=-1)
@click.pass_obj
def graph(obj, targets):
    graph = Graph.from_config(obj)

    # If targets supplyed only show dependencies for thoes targets
    # otherwise show the whole workflow
    matches = graph.targets.values()
    if targets:
        matches = filter_names(matches, targets)
        # TODO: Consider if the check below is useful, it would make sure
        #       that no empty pdf is created.
        #
        # Check for non existing targets
        #for target in targets:
        #    if target not in matches:
        #        raise GWFError(f'No target named {target} found in workflow')

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
