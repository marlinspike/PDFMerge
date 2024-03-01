import os
import glob
import argparse
import logging
import requests
import tempfile
from pypdf import PdfReader, PdfWriter
from urllib.parse import unquote, urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_file(url, destination_folder):
    """Downloads a PDF from a URL to the specified destination folder."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    # Create a temporary file within the specified directory
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=destination_folder, suffix='.pdf')
    for chunk in response.iter_content(chunk_size=8192):
        temp_file.write(chunk)
    temp_file.close()
    logging.info(f"Downloaded {url} to {temp_file.name}")
    return temp_file.name

class PDFMergerTool:
    def __init__(self, folder=".", output="merged.pdf", max_file_size=None, sources_file=None):
        self.folder = os.path.abspath(folder)
        self.output = output
        self.max_file_size = max_file_size
        self.sources_file = sources_file
        self.output_path = os.path.join(self.folder, self.output)
        self.temp_files = []
        self.bad_documents = []  # Initialize the bad_documents attribute

    def merge_pdfs(self):
        if self.sources_file:
            with open(self.sources_file, 'r') as f:
                urls = [line.strip() for line in f.readlines()]
                for url in urls:
                    try:
                        temp_file_path = download_file(url, self.folder)
                        self.temp_files.append(temp_file_path)
                    except Exception as e:
                        logging.error(f"Failed to download or process {url}: {e}")
                        self.bad_documents.append(url)
                        continue  # Skip to the next URL

        writer = PdfWriter()
        for temp_file in self.temp_files:
            try:
                reader = PdfReader(temp_file)
                for page in reader.pages:
                    try:
                        writer.add_page(page)
                    except Exception as e:
                        logging.error(f"Error processing page from {temp_file}; skipping page: {e}")
                        # Optionally, mark the whole document as bad and continue to the next document
            except Exception as e:
                logging.error(f"Error processing document {temp_file}; skipping document: {e}")
                self.bad_documents.append(temp_file)
            finally:
                # Ensure the temporary file is deleted regardless of the outcome
                os.remove(temp_file)
                logging.info(f"Deleted temporary file: {temp_file}")

        if writer.pages:
            with open(self.output_path, 'wb') as f_out:
                writer.write(f_out)
            logging.info(f"Merged PDF saved to {self.output_path}")
        else:
            logging.error("No pages were added to the output PDF.")

        if self.max_file_size:
            self.check_file_size_and_split()

        if self.bad_documents:
            logging.error(f"Bad documents encountered: {self.bad_documents}")
            # Handle bad_documents as needed, e.g., log them to a file or notify someone

    def read_sources_file(self):
        sources = []
        with open(self.sources_file, 'r') as file:
            for line in file:
                cleaned_line = line.strip()
                if cleaned_line:
                    sources.append(cleaned_line)
        return sources

    def find_pdf_files_in_folder(self):
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
