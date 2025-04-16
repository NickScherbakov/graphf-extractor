from manim import *

def generate_graph_and_matrix_script(nodes, edges, output_file="graph_manim.py"):
    # Генерируем текст manim-скрипта
    with open(output_file, "w") as f:
        f.write(f'''
from manim import *

class GraphToAdjacency(Scene):
    def construct(self):
        # 1. Построение графа
        vertices = {nodes}
        edges = {edges}
        g = Graph(vertices, edges, layout="circular")
        self.play(Create(g))
        self.wait(1)

        # 2. Поочерёдная подсветка рёбер
        edge_objs = [g.edges[e] for e in edges]
        for eo in edge_objs:
            self.play(eo.animate.set_color(RED), run_time=0.5)
            self.wait(0.2)
            self.play(eo.animate.set_color(WHITE), run_time=0.2)

        self.wait(0.5)

        # 3. Построение матрицы смежности
        matrix_data = self.get_adjacency_matrix(vertices, edges)
        mat = IntegerMatrix(matrix_data)
        mat.next_to(g, RIGHT, buff=1)
        self.play(FadeIn(mat))
        self.wait(1)

        # 4. Поочерёдная подсветка элементов матрицы для каждого ребра
        for e in edges:
            i = vertices.index(e[0])
            j = vertices.index(e[1])
            entry1 = mat.get_entries()[i*len(vertices)+j]
            entry2 = mat.get_entries()[j*len(vertices)+i]
            self.play(entry1.animate.set_color(YELLOW), entry2.animate.set_color(YELLOW), run_time=0.5)
            self.wait(0.2)
            self.play(entry1.animate.set_color(WHITE), entry2.animate.set_color(WHITE), run_time=0.2)
        self.wait(2)

    @staticmethod
    def get_adjacency_matrix(vertices, edges):
        n = len(vertices)
        idx = {{v: i for i, v in enumerate(vertices)}}
        mat = [[0]*n for _ in range(n)]
        for a, b in edges:
            i, j = idx[a], idx[b]
            mat[i][j] = 1
            mat[j][i] = 1  # для неориентированного графа
        return mat
''')

if __name__ == "__main__":
    # Пример использования
    nodes = ["A", "B", "C", "D"]
    edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("A", "C")]
    generate_graph_and_matrix_script(nodes, edges)