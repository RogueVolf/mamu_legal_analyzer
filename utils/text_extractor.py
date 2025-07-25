from pathlib import Path
from unstructured.partition.pdf import partition_pdf

def text_extractor(file_path: Path) -> str:
    elements = partition_pdf(filename=str(file_path))
    text = "\n\n".join([el.text for el in elements if el.text])
    return text