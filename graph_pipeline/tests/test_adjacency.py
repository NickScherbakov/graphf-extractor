from graph_pipeline.graph_structure_extractor import adjacency_matrix_from_edges

def test_adjacency_matrix_simple():
    nodes = ["A", "B", "C"]
    edges = [("A", "B"), ("B", "C")]
    expected = [
        [0, 1, 0],
        [1, 0, 1],
        [0, 1, 0]
    ]
    mat = adjacency_matrix_from_edges(nodes, edges)
    assert (mat == expected).all()