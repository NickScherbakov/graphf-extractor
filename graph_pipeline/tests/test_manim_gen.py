from graph_pipeline.generate_manim_advanced import generate_graph_and_matrix_script
import os

def test_generate_manim_script(tmp_path):
    nodes = ["X", "Y"]
    edges = [("X", "Y")]
    out_file = tmp_path / "test_graph_manim.py"
    generate_graph_and_matrix_script(nodes, edges, output_file=str(out_file))
    assert os.path.isfile(out_file)
    with open(out_file) as f:
        content = f.read()
        assert "class GraphToAdjacency(Scene):" in content