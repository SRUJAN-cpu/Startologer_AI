"""
Online PDF Compression Service
Uses iLovePDF API to compress large PDF files automatically
"""
import os
import time
from pylovepdf.ilovepdf import ILovePdf

def compress_pdf_online(input_path: str, output_path: str = None) -> str:
    """
    Compress PDF using iLovePDF API

    Args:
        input_path: Path to input PDF file
        output_path: Path for output (default: input_path with _compressed suffix)

    Returns:
        Path to compressed PDF file
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compressed{ext}"

    try:
        # Get API keys from environment
        public_key = os.environ.get('ILOVEPDF_PUBLIC_KEY')
        secret_key = os.environ.get('ILOVEPDF_SECRET_KEY')

        if not public_key or not secret_key:
            print("[OnlinePDFCompressor] No API keys found, falling back to local compression")
            return None

        print(f"[OnlinePDFCompressor] Compressing {input_path} using iLovePDF API...")

        # Initialize iLovePDF
        ilovepdf = ILovePdf(public_key, verify_ssl=True)

        # Create compress task
        task = ilovepdf.new_task('compress')

        # Upload file
        task.add_file(input_path)

        # Set compression level (recommended = balanced compression)
        task.set_output_folder(os.path.dirname(output_path))

        # Execute compression
        task.execute()

        # Download result
        task.download()

        # Get the downloaded file path
        downloaded_file = task.get_filename()

        # Rename to expected output path
        if downloaded_file != output_path:
            os.rename(downloaded_file, output_path)

        # Get file sizes
        input_size = os.path.getsize(input_path) / (1024 * 1024)
        output_size = os.path.getsize(output_path) / (1024 * 1024)
        savings = ((input_size - output_size) / input_size) * 100

        print(f"[OnlinePDFCompressor] Success! {input_size:.1f}MB → {output_size:.1f}MB (saved {savings:.1f}%)")

        return output_path

    except Exception as e:
        print(f"[OnlinePDFCompressor] Error: {e}")
        return None


def compress_pdf_with_fallback(input_path: str, output_path: str = None) -> str:
    """
    Compress PDF with automatic fallback to local compression

    Args:
        input_path: Path to input PDF file
        output_path: Path for output

    Returns:
        Path to compressed PDF (or original if compression fails)
    """
    # Try online compression first
    result = compress_pdf_online(input_path, output_path)

    if result and os.path.exists(result):
        return result

    # Fallback to local compression
    print("[OnlinePDFCompressor] Falling back to local PyPDF2 compression...")
    try:
        from helpers.pdf_compressor import compress_pdf
        return compress_pdf(input_path, output_path)
    except Exception as e:
        print(f"[OnlinePDFCompressor] Local compression also failed: {e}")
        return input_path  # Return original file if all compression fails
