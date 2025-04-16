from graphreader import GraphReader
import networkx as nx

def extract_graph_structure(image_path):
    gr = GraphReader()
    result = gr.read(image_path)
    edges = result["edges"]
    nodes = result["nodes"]
    return nodes, edges

def adjacency_matrix_from_edges(nodes, edges):
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    adj_matrix = nx.adjacency_matrix(G, nodelist=nodes).todense()
    return adj_matrix

if __name__ == "__main__":
    import sys
    nodes, edges = extract_graph_structure(sys.argv[1])
    print("Вершины:", nodes)
    print("Рёбра:", edges)
    adj = adjacency_matrix_from_edges(nodes, edges)
    print("Матрица смежности:\n", adj)