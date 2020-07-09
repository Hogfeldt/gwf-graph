import click
from graphviz import Digraph

from gwf.core import Graph

@click.command()
@click.pass_obj
def graph(obj):
    graph = Graph.from_config(obj)
    print(graph)
    dot = Digraph(comment='The Round Table')
    
    dot.node('A', 'King Arthur')
    dot.node('B', 'Sir Bedevere the Wise')
    dot.node('L', 'Sir Lancelot the Brave')

    dot.edges(['AB', 'AL'])
    dot.edge('B', 'L', constraint='false')
    dot.render('test-output/round-table.gv', view=True)


