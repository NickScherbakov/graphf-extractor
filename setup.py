from setuptools import setup, find_packages

setup(
    name="graph_pipeline",
    version="0.1.0",
    description="Пайплайн для поиска, распознавания и визуализации графов в документах PDF",
    author="NickScherbakov & Copilot",
    packages=find_packages(),
    install_requires=[
        "PyMuPDF",
        "graphreader",
        "networkx",
        "manim",
    ],
    entry_points={
        "console_scripts": [
            "graph-pipeline = graph_pipeline.main:main"
        ]
    },
    python_requires=">=3.8",
)