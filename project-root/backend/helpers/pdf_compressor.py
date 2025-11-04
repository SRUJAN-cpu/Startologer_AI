"""
PDF Compression Utility
Compresses large PDF files to reduce size before processing.
"""
import os
from PyPDF2 import PdfReader, PdfWriter

def compress_pdf(input_path: str, output_path: str = None, compression_level: int = 9) -> str:
    """
    Compress a PDF file by removing redundant content and optimizing.

    Args:
        input_path: Path to input PDF file
        output_path: Path for compressed output (default: overwrites input)
        compression_level: Compression level 0-9 (9 = maximum compression)

    Returns:
        Path to compressed PDF file
    """
    if output_path is None:
        output_path = input_path.replace('.pdf', '_compressed.pdf')

    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        # Copy all pages with compression
        for page in reader.pages:
            page.compress_content_streams()  # This is CPU intensive but reduces file size
            writer.add_page(page)

        # Write compressed PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        input_size = os.path.getsize(input_path)
        output_size = os.path.getsize(output_path)
        compression_ratio = (1 - output_size / input_size) * 100

        print(f"[PDF Compression] Original: {input_size / (1024*1024):.2f}MB -> Compressed: {output_size / (1024*1024):.2f}MB (saved {compression_ratio:.1f}%)")

        return output_path

    except Exception as e:
        print(f"[PDF Compression] Failed to compress {input_path}: {e}")
        # If compression fails, return original file
        return input_path

def should_compress_pdf(file_path: str, threshold_mb: int = 10) -> bool:
    """
    Check if a PDF file should be compressed based on size.

    Args:
        file_path: Path to PDF file
        threshold_mb: Size threshold in MB above which compression is triggered

    Returns:
        True if file should be compressed, False otherwise
    """
    if not file_path.lower().endswith('.pdf'):
        return False

    if not os.path.exists(file_path):
        return False

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb > threshold_mb
