import os
import glob
import argparse
import logging
import requests
from pypdf import PdfReader, PdfWriter
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_file(url, destination_folder):
    """Downloads a file from a URL to the specified destination folder."""
    local_filename = os.path.join(destination_folder, urlparse(url).path.split('/')[-1])
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

class PDFMerger:
    def __init__(self, folder=".", output="merged.pdf", max_file_size=None, sources_file=None):
        self.folder = os.path.abspath(folder)
        self.output = output
        self.max_file_size = max_file_size  # in MB
        self.sources_file = sources_file
        self.output_path = os.path.join(self.folder, self.output)

    def merge_pdfs(self):
        pdf_files = self.read_sources() if self.sources_file else self.find_pdf_files()
        
        if not pdf_files:
            logging.warning("No PDF files found to process.")
            return
        
        writer = PdfWriter()
        
        for pdf_file in pdf_files:
            try:
                logging.info(f"Processing {pdf_file}")
                if pdf_file.startswith("http"):
                    pdf_file = download_file(pdf_file, self.folder)
                reader = PdfReader(pdf_file)
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                logging.error(f"Failed to process {pdf_file}: {e}")
        
        try:
            logging.info("Starting to write merged PDF...")
            with open(self.output_path, 'wb') as f:
                writer.write(f)
            logging.info(f"Merged PDF saved to {self.output_path}")
        except Exception as e:
            logging.error(f"Failed to write merged PDF: {e}")
        
        if self.max_file_size:
            self.check_file_size_and_split()

    def read_sources(self):
        """Reads PDF file paths or URLs from a given sources file."""
        with open(self.sources_file, 'r') as file:
            lines = file.read().splitlines()
        return [line.strip() for line in lines if line.strip()]

    def find_pdf_files(self):
        """Finds PDF files in the specified folder."""
        return glob.glob(os.path.join(self.folder, '*.pdf'))

    def check_file_size_and_split(self):
        """Checks the file size of the merged PDF and splits it if it exceeds the max file size."""
        file_size_mb = os.path.getsize(self.output_path) / (1024 * 1024)  # Convert to MB
        if file_size_mb <= self.max_file_size:
            logging.info("No need to split the PDF as it's within the size limit.")
            return

        reader = PdfReader(self.output_path)
        total_pages = len(reader.pages)
        pages_per_mb = total_pages / file_size_mb  # Estimate pages per MB

        estimated_pages_per_part = int(pages_per_mb * self.max_file_size)
        parts = max(1, total_pages // estimated_pages_per_part)

        logging.info(f"Splitting the PDF into {parts} parts...")
        for part in range(parts):
            writer = PdfWriter()
            start_page = part * estimated_pages_per_part
            end_page = start_page + estimated_pages_per_part if part < parts - 1 else total_pages

            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])

            part_filename = f"{self.output[:-4]}-part{part + 1}.pdf"
            part_path = os.path.join(self.folder, part_filename)
            with open(part_path, 'wb') as f:
                writer.write(f)
            logging.info(f"Written part {part + 1} to {part_filename}")

        # Optionally, remove the original large file
        os.remove(self.output_path)
        logging.info("Original merged PDF removed due to size splitting.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge PDFs from files or URLs and optionally split the merged PDF if it exceeds a specified size.")
    parser.add_argument("-f", "--folder", default=".", help="Folder to save downloaded PDFs and the output merged PDF file.")
    parser.add_argument("-o", "--output", default="merged.pdf", help="Name of the output merged PDF file.")
    parser.add_argument("-s", "--size", type=float, help="Maximum file size in MB for the output PDF. If the merged file is larger, it will be split into smaller parts.")
    parser.add_argument("-l", "--list", dest="sources_file", help="Path to a new-line delimited file containing PDF files or URLs to merge.")

    args = parser.parse_args()

    tool = PDFMerger(folder=args.folder, output=args.output, max_file_size=args.size, sources_file=args.sources_file)
    tool.merge_pdfs()
