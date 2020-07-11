import click
from graphviz import Digraph

from gwf.core import Graph
from gwf.filtering import filter_names
from gwf.exceptions import GWFError

first = lambda p: p[0]

@click.command()
@click.argument('targets', nargs=-1)
@click.option('--output-type', type=click.Choice(['graphviz', 'cytoscape']), default='graphviz')
@click.pass_obj
def graph(obj, targets, output_type):
    graph = Graph.from_config(obj)

    # If targets supplyed only show dependencies for thoes targets
    # otherwise show the whole workflow
    matches = graph.targets.values()
    if targets:
        matches = filter_names(matches, targets)
        # Prevent drawing an empty graph
        if not matches:
            raise GWFError('Non of the targets was found in the workflow')

    if output_type == 'graphviz':
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
                    dot.edge(name, dep_target.name, arrowsize='.5')
                visited.add(name)
        dot.render('dependency_graph.gv')
    elif output_type == 'cytoscape':
        pass
