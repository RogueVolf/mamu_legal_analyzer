import json
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from collections import defaultdict

file_path = ""
base_file_name = r"C:/Users/Wolf/Downloads/test"

def main():
    elements = partition_pdf(filename=f"{base_file_name}.pdf")
    # Group by title and body under that title

    structured_blocks = chunk_by_title(elements)
    sanitized_blocks = []
    
    for block in structured_blocks:
        print(block.to_dict())
        sanitized_blocks.append(block.text)
    with open("structured_output.json", "w", encoding="utf-8") as f:
        json.dump(sanitized_blocks, f, indent=2)


if __name__ == "__main__":
    main()