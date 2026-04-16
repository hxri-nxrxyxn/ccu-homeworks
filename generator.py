import re
import subprocess
import requests
from pathlib import Path
from config import OLLAMA_URL, MODEL_NAME, TEMP_DIR

class LatexGenerator:
    def __init__(self):
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)

    async def generate_solution(self, prompt: str) -> str:
        """Calls local Ollama to generate strict LaTeX code."""
        system_msg = (
            "You are a LaTeX expert. Output ONLY valid, compile-ready LaTeX code. "
            "Include documentclass, all necessary packages, and the document body. "
            "Do not include any introductory text, markdown code blocks (```latex), "
            "or explanations. Just the raw LaTeX source code."
        )
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": f"{system_msg}\n\nAssignment Prompt: {prompt}",
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            latex_code = response.json().get("response", "").strip()
            
            # Strip potential markdown artifacts
            latex_code = re.sub(r"```latex|```", "", latex_code).strip()
            return latex_code
        except Exception as e:
            print(f"Ollama Error: {e}")
            return ""

    def compile_pdf(self, latex_content: str, filename: str) -> Path:
        """Compiles LaTeX string to PDF using pdflatex."""
        tex_path = self.temp_dir / f"{filename}.tex"
        pdf_path = self.temp_dir / f"{filename}.pdf"
        
        tex_path.write_text(latex_content)
        
        try:
            # Run pdflatex twice for references/toc if needed
            for _ in range(1):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(self.temp_dir), str(tex_path)],
                    check=True,
                    capture_output=True
                )
            return pdf_path if pdf_path.exists() else None
        except subprocess.CalledProcessError as e:
            print(f"LaTeX Compilation Error: {e.stderr.decode()}")
            return None

    def cleanup(self, filename: str):
        """Removes temporary build files."""
        for f in self.temp_dir.glob(f"{filename}.*"):
            if f.suffix != ".pdf": # Keep PDF if needed, or remove all
                f.unlink()
