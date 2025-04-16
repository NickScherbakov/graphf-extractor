import os
import tempfile
from graph_pipeline.extract_graph_image import extract_images_from_pdf

def test_extract_images_from_pdf():
    # Пример теста: должен извлекать хотя бы одно изображение из PDF с изображениями
    # Используйте свой тестовый PDF-файл с известным количеством изображений
    test_pdf = os.path.join(os.path.dirname(__file__), "test_graph.pdf")
    if not os.path.isfile(test_pdf):
        # Скип, если файла нет (CI не должен падать)
        return
    with tempfile.TemporaryDirectory() as tmpdir:
        images = extract_images_from_pdf(test_pdf, output_dir=tmpdir)
        assert len(images) > 0