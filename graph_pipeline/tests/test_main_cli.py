import subprocess
import sys
import os

def test_main_cli_help():
    # Проверяет, что CLI запускается и выдаёт help
    result = subprocess.run([sys.executable, "-m", "graph_pipeline.main", "--help"], capture_output=True, text=True)
    assert "usage" in result.stdout.lower()
    assert result.returncode == 0