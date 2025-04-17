from graph_pipeline.generate_manim_advanced import generate_graph_and_matrix_script

def test_generate_script(tmp_path):
    nodes = [...]
    edges = [...]
    adj_matrix = [...]
    output_file = tmp_path / "out.py"
    result = generate_graph_and_matrix_script(nodes, edges, adj_matrix, str(output_file))
    assert result is True
    assert output_file.exists()