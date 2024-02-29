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
    """Downloads a PDF from a URL to the specified destination folder."""
    local_filename = os.path.join(destination_folder, urlparse(url).path.split('/')[-1])
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    logging.info(f"Downloaded {local_filename}")
    return local_filename

class PDFMergerTool:
    def __init__(self, folder=".", output="merged.pdf", max_file_size=None, sources_file=None):
        self.folder = os.path.abspath(folder)
        self.output = output
        self.max_file_size = max_file_size  # in MB
        self.sources_file = sources_file
        self.output_path = os.path.join(self.folder, self.output)

    def merge_pdfs(self):
        """Merges PDFs from specified folder or a list of URLs/files."""
        pdf_files = self.read_sources_file() if self.sources_file else self.find_pdf_files_in_folder()
        
        writer = PdfWriter()
        
        for pdf_file in pdf_files:
            try:
                if pdf_file.startswith("http"):
                    pdf_file = download_file(pdf_file, self.folder)
                logging.info(f"Processing {pdf_file}")
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

    def read_sources_file(self):
        """Reads PDF sources (file paths or URLs) from a provided newline-separated file."""
        sources = []
        with open(self.sources_file, 'r') as file:
            for line in file:
                cleaned_line = line.strip()
                if cleaned_line:  # Ensure the line is not empty
                    sources.append(cleaned_line)
        return sources

    def find_pdf_files_in_folder(self):
        """Finds all PDF files in the specified folder."""
        return glob.glob(os.path.join(self.folder, '*.pdf'))

    def check_file_size_and_split(self):
        file_size_mb = os.path.getsize(self.output_path) / (1024 * 1024)  # size in MB
        if file_size_mb <= self.max_file_size:
            logging.info("Merged file is within the size limit.")
            return  # No need to split

        logging.info("Splitting the merged PDF into smaller parts...")
        reader = PdfReader(self.output_path)
        total_pages = len(reader.pages)

        # Estimate the number of parts needed based on the file size and the limit
        parts = max(1, int(file_size_mb / self.max_file_size) + 1)
        pages_per_part = total_pages // parts

        for part in range(parts):
            writer = PdfWriter()
            start_page = part * pages_per_part
            end_page = start_page + pages_per_part if part < parts - 1 else total_pages

            for page_num in range(start_page, end_page):
                writer.add_page(reader.pages[page_num])

            part_filename = f"{self.output[:-4]}-part{part + 1}.pdf"
            with open(os.path.join(self.folder, part_filename), 'wb') as f_out:
                writer.write(f_out)

            logging.info(f"Written part {part + 1} to {part_filename}")

        # Optionally, remove the original large file
        os.remove(self.output_path)
        logging.info("Original merged PDF removed after splitting.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge PDFs from local files or URLs specified in an external file, with options to split the merged PDF.")
    parser.add_argument("-f", "--folder", default=".", help="Folder to find local PDF files or save downloaded PDFs.")
    parser.add_argument("-o", "--output", default="merged.pdf", help="Filename for the output merged PDF.")
    parser.add_argument("-s", "--size", type=float, help="Maximum file size in MB for the merged PDF, triggering splitting if exceeded.")
    parser.add_argument("-l", "--list", dest="sources_file", help="Path to a file containing a newline-separated list of PDF URLs or file paths to merge.")

    args = parser.parse_args()

    tool = PDFMergerTool(folder=args.folder, output=args.output, max_file_size=args.size, sources_file=args.sources_file)
    tool.merge_pdfs()
