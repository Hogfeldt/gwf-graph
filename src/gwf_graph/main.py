import csv
from functools import partial
from itertools import chain

import click
from graphviz import Digraph

from gwf.core import Graph
from gwf.filtering import filter_names
from gwf.exceptions import GWFError

first = lambda p: p[0]

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
        for target in visit_all_dependencies(graph, matches):
            name = target.name
            dot.node(name, name)    #shape='parallelogram'
            for dep_target in graph.dependencies[target]:
                dot.edge(name, dep_target.name, arrowsize='.5')
        dot.render('dependency_graph.gv')
    elif output_type == 'cytoscape':
        with open('dependency_graph.sif', 'w') as fp:
            writer = csv.writer(fp, delimiter=' ')
            for target in visit_all_dependencies(graph, matches):
                name = target.name
                dependencies = list(map(lambda d: d.name, graph.dependencies[target]))
                if dependencies:
                    writer.writerow([name, 'dependencies'] + dependencies)
