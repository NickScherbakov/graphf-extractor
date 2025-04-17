class GraphRecognitionResult:
    def __init__(self):
        self.vertices = []
        self.edges = []
        self.adjacency_matrix = []

class GraphRecognizer:
    def __init__(self):
        pass
        
    def recognize(self, image):
        # Здесь будет логика распознавания графа
        result = GraphRecognitionResult()
        
        # Временные тестовые данные
        result.vertices = ['A', 'Б', 'B', 'Г', 'Д', 'E', 'K']
        result.edges = [
            ('A', 'Б'), ('A', 'B'), 
            ('Б', 'B'), ('B', 'Г'),
            ('B', 'E'), ('Д', 'E'),
            ('Г', 'E'), ('E', 'K')
        ]
        
        # Создание матрицы смежности
        size = len(result.vertices)
        result.adjacency_matrix = [[0] * size for _ in range(size)]
        
        return result