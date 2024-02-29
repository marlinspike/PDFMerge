import os
import glob
import argparse
import logging
import requests
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_file(url, destination_folder):
    local_filename = os.path.join(destination_folder, urlparse(url).path.split('/')[-1])
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

class PDFMergerTool:
    def __init__(self, folder=".", output="merged.pdf", max_file_size=None, sources_file=None):
        self.folder = os.path.abspath(folder)
        self.output = output
        self.max_file_size = max_file_size
        self.sources_file = sources_file
        self.output_path = os.path.join(self.folder, self.output)
        
    def merge_pdfs(self):
        if self.sources_file:
            pdf_files = self.read_sources_file()
        else:
            pdf_files = glob.glob(os.path.join(self.folder, '*.pdf'))
        
        if not pdf_files:
            logging.warning("No PDF files found to process.")
            return
        
        merger = PdfMerger()
        
        for pdf_file in pdf_files:
            logging.info(f"Processing {pdf_file}")
            if pdf_file.startswith("http"):
                pdf_file = download_file(pdf_file, self.folder)
                logging.info(f"Downloaded {pdf_file}")
            merger.append(pdf_file)
        
        logging.info("Starting to write merged PDF...")
        merger.write(self.output_path)
        merger.close()
        logging.info(f"Merged PDF saved to {self.output_path}")
        
        if self.max_file_size is not None:
            self.check_file_size_and_split()
    
    def read_sources_file(self):
        with open(self.sources_file, 'r') as file:
            lines = file.read().splitlines()
        return [line.strip() for line in lines if line.strip()]
    
    # Other methods remain unchanged...

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge PDFs from files or URLs and optionally split the merged PDF.")
    parser.add_argument("-f", "--folder", default=".", help="Folder to save downloaded PDFs and the output merged PDF.")
    parser.add_argument("-o", "--output", default="merged.pdf", help="Name of the output merged PDF file.")
    parser.add_argument("-s", "--size", type=float, help="Maximum file size in MB for the output PDF. It will be split if exceeded.")
    parser.add_argument("-l", "--list", dest="sources_file", help="Path to a new-line delimited file containing PDF files or URLs.")

    args = parser.parse_args()

    tool = PDFMergerTool(folder=args.folder, output=args.output, max_file_size=args.size, sources_file=args.sources_file)
    tool.merge_pdfs()
