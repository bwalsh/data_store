"""Test nested object to graph."""

from collections import namedtuple
from pprint import pprint
import hashlib
import json

import redis
from redisgraph import Node, Edge, Graph, Path


Vertex = namedtuple('Vertex', ['vertex', 'edges', 'label', 'alias'])


def is_simple(v):
    """Return True if scalar or list of scalars."""
    if not isinstance(v, dict) and not isinstance(v, list):
        return True
    if isinstance(v, list):
        if len(v) == 0:
            return True
        # spot check first val
        return is_simple(v[0])
    return False


class DocumentReader(object):
    """Read dictionary-like thing covert to nested property graph of vertices and edges."""

    def get_alias(self, properties, label):
        """Figure out the alias."""
        """MD5 hash of a dictionary."""
        dhash = hashlib.md5()
        # We need to sort arguments so {'a': 1, 'b': 2} is
        # the same as {'b': 2, 'a': 1}
        encoded = json.dumps(properties, sort_keys=True).encode()
        dhash.update(encoded)
        return dhash.hexdigest()

    def to_edges(self, dict_or_list, label='root'):
        """Return vertex, outbound edges and child vertices."""
        if isinstance(dict_or_list, dict):
            properties = {k: v for k, v in dict_or_list.items() if is_simple(v)}
            alias = self.get_alias(properties, label)
            return Vertex(
                vertex=properties,
                edges=[{k: self.to_edges(v, k) for k, v in dict_or_list.items() if not is_simple(v)}],
                label=label,
                alias=alias
            )
        elif isinstance(dict_or_list, list):
            print(f"is list {dict_or_list}")
            return [self.to_edges(i, label) for i in dict_or_list]
        else:
            return dict_or_list


class DocumentWriter(object):
    """Write graphified document to graph."""

    def persist_vertex(self, vertex, label, alias):
        """Persist vertex, return node."""
        print(f"persist_vertex label:{label}, alias:{alias}, contents:{vertex}")
        return vertex

    def persist_edge(self, _from, edge):
        """Persist edge."""
        if not edge:
            return
        print(_from)
        for k, v in edge.items():
            print(f"edge name: {k}")
            if not isinstance(v, list):
                node = self.persist_vertex(v.vertex, v.label, v.alias)
                print(f"persist_edge from {_from}->{k}->")
                print(f"   ...{v.label}:{v.alias}")
                self.to_graph(v, node)
            else:
                for i in v:
                    node = self.persist_vertex(i.vertex, i.label, i.alias)
                    print(f"persist_edge {_from}->{k}->{i.label}:{i.alias}")
                    self.to_graph(i, node)

    def to_graph(self, v, node=None):
        """Persist vertex and edges."""
        if not node:
            print("before save")
            node = self.persist_vertex(v.vertex, v.label, v.alias)            
        for e in v.edges:
            self.persist_edge(node, e)


class RedisGraphDocumentWriter(DocumentWriter):
    """Persists to RedisGraph."""

    def __init__(self, graph) -> None:
        """Initialize state."""
        super().__init__()
        self.graph = graph

    def persist_vertex(self, vertex, label, alias):
        """Persist vertex."""
        print(f"persist_vertex label:{label}, alias:{alias}, contents:{vertex}")
        n = Node(label=label, properties=vertex)  # , alias=alias)
        self.graph.add_node(n)
        return n

    def persist_edge(self, _from, edge):
        """Persist edge."""
        if not edge:
            return
        print(_from)
        for k, v in edge.items():
            print(f"edge name: {k}")
            if not isinstance(v, list):
                node = self.persist_vertex(v.vertex, v.label, v.alias)
                print(f"persist_edge from {_from}->{k}->")
                print(f"   ...{v.label}:{v.alias}")
                edge = Edge(_from, k, node)
                self.graph.add_edge(edge)
                self.to_graph(v, node)
            else:
                for i in v:
                    node = self.persist_vertex(i.vertex, i.label, i.alias)
                    print(f"persist_edge {_from}->{k}->{i.label}:{i.alias}")
                    edge = Edge(_from, k, node)
                    self.graph.add_edge(edge)
                    self.to_graph(i, node)



reader = DocumentReader()

# print(reader.to_edges({'a': 'A', 'child': {'c': 'C'}}, 'parent'))

# print(reader.to_edges({'a': 'A', 'girl': {'g': 'G'}, 'boy': {'b': 'B'}}))

# print(reader.to_edges({'a': 'A', 'girl': {'g': 'G'}, 'boy': {'b': 'B', 'friend': {'f': 'F'}}}))

# print(reader.to_edges({'a': 'A', 'girl': {'g': 'G'}, 'boy': {'b': 'B', 'friend': {'f': 'F'}, 'favorite_colors': ['green', 'blue']}}))

# writer = DocumentWriter()
# writer.to_graph(reader.to_edges({'a': 'A', 'girl': {'g': 'G'}, 'boy': {'b': 'B', 'friend': [{'f': 'F1'}, {'f': 'F2'}]}}, 'parent'))


g = Graph(name='test3', redis_con=redis.Redis(host='redisgraph', port=6379))
writer = RedisGraphDocumentWriter(g)
writer.to_graph(reader.to_edges({'a': 'A', 'girl': {'g': 'G'}, 'boy': {'b': 'B', 'friend': [{'f': 'F1'}, {'f': 'F2'}]}}, 'parent'))
g.commit()

result = g.query("""Match (n)-[r]->(m) Return n,r,m""")
result.pretty_print()
for n,r,m in result.result_set:
    print(n,r,m)


result = g.query("""MATCH (n) RETURN n""")
result.pretty_print()
for record in result.result_set:
    print(record[0], record[0].id, record[0].alias)

g.delete()
g.commit()    