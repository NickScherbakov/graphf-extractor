import fitz  # PyMuPDF
import os

def extract_images_from_pdf(pdf_path, output_dir="pdf_images"):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        images = page.get_images(full=True)
        for img_idx, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_path = os.path.join(output_dir, f"page{page_idx+1}_img{img_idx+1}.png")
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            image_paths.append(image_path)
    return image_paths

if __name__ == "__main__":
    import sys
    image_paths = extract_images_from_pdf(sys.argv[1])
    print("Извлечённые изображения:", image_paths)