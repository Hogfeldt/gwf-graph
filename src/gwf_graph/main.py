import click
from graphviz import Digraph

from gwf.core import Graph

@click.command()
@click.pass_obj
def graph(obj):
    graph = Graph.from_config(obj)
    dot = Digraph(comment='Dependency Graph')
    for node in graph.targets.keys():
        target = graph.targets[node]
        name = target.name
        dot.node(name, name)
        for dep_target in graph.dependents[target]:
            dot.edge(name, dep_target.name)
    dot.render('dependency_graph.gv')
