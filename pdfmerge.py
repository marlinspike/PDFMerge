import os
import argparse
import logging
import requests
import tempfile
from pypdf import PdfReader, PdfWriter
import fitz 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OutputStrategy:
    def output(self, content, path):
        raise NotImplementedError

class PdfOutputStrategy(OutputStrategy):
    def output(self, content, path):
        writer = PdfWriter()
        for page_content in content:
            writer.add_page(page_content)
        with open(path, 'wb') as out_file:
            writer.write(out_file)
        logging.info(f"PDF output saved to {path}")

class MarkdownOutputStrategy(OutputStrategy):
    def output(self, pdf_paths, markdown_path):
        all_text = ""
        for pdf_path in pdf_paths:
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    all_text += f"## Document: {os.path.basename(pdf_path)}, Page: {page_num+1}\n\n{text}\n\n"
                doc.close()
            except Exception as e:
                logging.error(f"Failed to process PDF {pdf_path}: {e}")
        with open(markdown_path, 'w', encoding='utf-8') as md_file:
            md_file.write(all_text)
        logging.info(f"Markdown output saved to {markdown_path}")


def download_file(url, destination_folder):
    """Downloads a PDF from a URL to the specified destination folder."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=destination_folder, suffix='.pdf')
    for chunk in response.iter_content(chunk_size=8192):
        temp_file.write(chunk)
    temp_file.close()
    logging.info(f"Downloaded {url} to {temp_file.name}")
    return temp_file.name

class PDFMergerTool:
    def __init__(self, folder=".", output="merged.pdf", max_file_size=None, sources_file=None, output_markdown=False):
        self.folder = os.path.abspath(folder)
        self.output = output
        self.max_file_size = max_file_size
        self.sources_file = sources_file
        self.output_markdown = output_markdown
        self.output_path = os.path.join(self.folder, self.output)
        self.bad_documents = []  # Initialize the bad_documents attribute

    def merge_pdfs(self):
        downloaded_pdfs = []  # Store paths of successfully downloaded PDFs
        if self.sources_file:
            with open(self.sources_file, 'r') as f:
                urls = [line.strip() for line in f.readlines()]
                for url in urls:
                    try:
                        temp_file_path = download_file(url, self.folder)
                        downloaded_pdfs.append(temp_file_path)  # Add to list if successful
                    except Exception as e:
                        logging.error(f"Failed to download or process {url}; skipping.")
                        self.bad_documents.append(url)

        if self.output_markdown:
            # Output in Markdown format
            markdown_strategy = MarkdownOutputStrategy()
            markdown_path = os.path.join(self.folder, f"{os.path.splitext(self.output)[0]}.md")
            markdown_strategy.output(downloaded_pdfs, markdown_path)
        else:
            # Merge PDFs into one
            content = []
            for pdf_path in downloaded_pdfs:
                try:
                    reader = PdfReader(pdf_path)
                    content.extend(reader.pages)
                except Exception as e:
                    logging.error(f"Failed to process PDF {pdf_path}; skipping.")
                    self.bad_documents.append(pdf_path)
                finally:
                    os.remove(pdf_path)  # Clean up downloaded PDF

            if content:
                pdf_strategy = PdfOutputStrategy()
                pdf_strategy.output(content, self.output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge PDFs and optionally report bad documents in Markdown.")
    parser.add_argument("-f", "--folder", default=".", help="Folder to find local PDF files or save downloaded PDFs.")
    parser.add_argument("-o", "--output", default="merged.pdf", help="Filename for the output merged PDF.")
    parser.add_argument("-s", "--size", type=float, help="Maximum file size in MB for the merged PDF, triggering splitting if exceeded.")
    parser.add_argument("-l", "--list", dest="sources_file", help="Path to a file containing PDF URLs or file paths to merge.")
    parser.add_argument("-m", "--markdown", action="store_true", help="Output a Markdown report of bad documents.")

    args = parser.parse_args()

    tool = PDFMergerTool(folder=args.folder, output=args.output, max_file_size=args.size, sources_file=args.sources_file, output_markdown=args.markdown)
    tool.merge_pdfs()
