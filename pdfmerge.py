import os
import argparse
import logging
import requests
import tempfile
from pypdf import PdfReader, PdfWriter
import fitz 
import aiohttp
import asyncio
from tqdm import tqdm
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OutputStrategy:
    def output(self, content, path):
        raise NotImplementedError

class PdfOutputStrategy(OutputStrategy):
    def output(self, content, path):
        writer = PdfWriter()
        current_pdf = None
        for pdf_name, page_content in content:
            if pdf_name != current_pdf:
                logging.info(f"Processing PDF: {pdf_name}")
                current_pdf = pdf_name
            writer.add_page(page_content)
        with open(path, 'wb') as out_file:
            writer.write(out_file)
        logging.info(f"PDF output saved to {path}")

import os
from tqdm import tqdm

class MarkdownOutputStrategy(OutputStrategy):
    async def output(self, pdf_paths, markdown_path, max_size_bytes=None):
        """
        Outputs extracted text from PDF paths to a markdown file. If the maximum size is specified,
        the output will be split into multiple parts.
        """
        all_text = ""
        for pdf_path in tqdm(pdf_paths, desc="Processing PDFs for Markdown"):
        #for pdf_path in pdf_paths:
            all_text += self.process_pdf(pdf_path)  # Correctly calls the method defined below


        # Write the single large Markdown file
        with open(markdown_path, 'w', encoding='utf-8') as md_file:
            md_file.write(all_text)
        logging.info(f"Markdown output saved to {markdown_path}")

        # Check file size and split if necessary
        file_size_bytes = os.path.getsize(markdown_path)
        if max_size_bytes and file_size_bytes > max_size_bytes:
            #self.split_and_save_markdown(markdown_path, max_size_bytes)
            self.split_markdown_file(markdown_path, max_size_bytes)

    #Optimized Split
    def split_markdown_file(self, markdown_path, max_size_bytes):
        # Get the size of the file
        file_size = os.path.getsize(markdown_path)
        # Calculate the number of parts needed
        num_parts = math.ceil(file_size / max_size_bytes)  # Use math.ceil to round up
        
        with open(markdown_path, 'rb') as file:
            content = file.read()
            
        # Calculate the size of each part
        part_size = math.ceil(len(content) / num_parts)
        
        for part in range(1, num_parts + 1):
            part_content = content[(part - 1) * part_size:part * part_size]
            # Define the filename for this part
            part_filename = f"{markdown_path[:-3]}_part_{part}.md"
            
            # Write this part to a new file
            with open(part_filename, 'wb') as part_file:
                part_file.write(part_content)
        
        # Optionally, delete the original file after splitting
        os.remove(markdown_path)

    #Deprecated
    def split_and_save_markdown(self, markdown_path, max_size_bytes):
        """
        Deprecated. Splits the markdown file into parts if its size exceeds the maximum allowed size.
        """
        with open(markdown_path, 'r', encoding='utf-8') as md_file:
            content_lines = md_file.readlines()

        parts = []
        current_part = ""
        # Accumulate lines until the part exceeds the max size
        for line in content_lines:
            if len(current_part.encode('utf-8')) + len(line.encode('utf-8')) > max_size_bytes:
                parts.append(current_part)
                current_part = line
            else:
                current_part += line
        parts.append(current_part) # Add the last part if any

        base_path, ext = os.path.splitext(markdown_path)
        # If only one part and it's the first, no need to split
        if len(parts) > 1:
            # Delete the original large file to replace with split parts
            os.remove(markdown_path)
            # Save each part to a separate file
            for i, part in enumerate(tqdm(parts, desc="Saving Markdown parts"), start=1):
                part_filename = f"{base_path}-part{i}{ext}"
                with open(part_filename, 'w', encoding='utf-8') as md_file:
                    md_file.write(part)
                logging.info(f"Markdown part {i} saved to {part_filename}")
        else:
            logging.info("No need to split the Markdown file; size is within the limit.")

        
    def process_pdf(self, pdf_path):
        """
        Processes a single PDF file, extracting text from each page and formatting it for Markdown.

        Args:
            pdf_path (str): Path to the PDF file to be processed.

        Returns:
            str: The extracted text from the PDF, formatted for Markdown.
        """
        text = ""
        #logging.info(f"Processing PDF for Markdown output: {pdf_path}")
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += f"## Document: {os.path.basename(pdf_path)}, Page: {page_num+1}\n\n{page.get_text()}\n\n"
            doc.close()
            logging.info(f"Successfully processed {pdf_path} for Markdown output")
        except Exception as e:
            logging.error(f"Failed to process PDF {pdf_path}: {e}")
        return text


class PDFMergerTool:
    def __init__(self, folder=".", output="merged.pdf", max_file_size=None, sources_file=None, output_markdown=False):
        self.folder = os.path.abspath(folder)
        self.output = output
        # Convert max_file_size from MB to bytes
        self.max_file_size = max_file_size * 1024 * 1024 if max_file_size else None
        self.sources_file = sources_file
        self.output_markdown = output_markdown
        self.output_path = os.path.join(self.folder, self.output)
        self.bad_documents = []
        self.temp_folder = os.path.join(self.folder, "temp")  # Ensure this line is correctly placed

    @staticmethod
    async def download_file(session, url, destination_folder):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        # Ensure the destination folder exists
        os.makedirs(destination_folder, exist_ok=True)
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=destination_folder, suffix='.pdf')
            async for chunk in response.content.iter_chunked(8192):
                temp_file.write(chunk)
            temp_file.close()
            logging.info(f"Downloaded {url} to {temp_file.name}")
            return temp_file.name

            
    async def merge_pdfs(self):
        """
    Asynchronously merges PDF files from URLs specified in the sources file or existing PDF files in a folder,
    saves the merged result as a single PDF, and optionally splits it into smaller parts if it exceeds a size limit.

    This method performs several key steps:
    1. It ensures the existence of a temporary folder for storing downloaded PDFs.
    2. It reads URLs from the sources file and asynchronously downloads PDFs from these URLs into the temporary folder.
       - Each PDF is downloaded using asynchronous HTTP requests to improve performance.
       - Downloaded PDFs are saved with unique temporary filenames within the temporary folder.
    3. After downloading, the method decides the output format based on the `output_markdown` flag.
       - If `output_markdown` is True, it processes the downloaded PDFs for text extraction and saves the text in a Markdown file.
       - If `output_markdown` is False, it merges the pages of all downloaded PDFs into a single PDF file.
    4. For PDF merging:
       - The method iterates over each downloaded PDF, reads its pages, and adds them to the merged PDF content.
       - The merged PDF is then saved to the output path specified by `self.output_path`.
    5. After merging, if the size of the merged PDF exceeds the specified maximum file size (`self.max_file_size`), the PDF is split:
       - The method calculates the number of pages per part based on the total size and the maximum file size limit.
       - It then creates new PDF files for each part, ensuring that each part does not exceed the size limit.
       - The original merged PDF is removed after splitting to avoid duplication and save disk space.

    This method leverages asynchronous programming for downloading PDFs to improve efficiency, especially when dealing with multiple sources.
    It also uses the filesystem for intermediate storage of PDFs, allowing for direct manipulation of files without the need for passing large objects in memory.

    Attributes:
        self.temp_folder (str): The path to the temporary folder for storing downloaded PDFs.
        self.output_path (str): The path where the merged (and potentially split) PDF will be saved.
        self.max_file_size (int): The maximum file size in bytes. If the merged PDF exceeds this size, it will be split.

    Raises:
        Exception: If downloading, merging, or splitting PDFs encounters an error, relevant exceptions are logged.
    """

        # Ensure temp folder exists
        os.makedirs(self.temp_folder, exist_ok=True)
        downloaded_pdfs = []
        if self.sources_file:
            async with aiohttp.ClientSession() as session:
                with open(self.sources_file, 'r') as f:
                    urls = [line.strip() for line in f.readlines()]
                    download_tasks = [self.download_file(session, url, self.temp_folder) for url in urls]
                    downloaded_pdfs = await asyncio.gather(*download_tasks, return_exceptions=True)
                    for result in downloaded_pdfs:
                        if isinstance(result, Exception):
                            logging.error(f"Failed to download or process a document: {result}")
                            self.bad_documents.append(str(result))
                        else:
                            logging.info(f"Successfully downloaded: {result}")

        if self.output_markdown:
            markdown_path = os.path.join(self.folder, f"{os.path.splitext(self.output)[0]}.md")
            markdown_strategy = MarkdownOutputStrategy()
            await markdown_strategy.output(downloaded_pdfs, markdown_path, self.max_file_size)
        else:
            # Merge PDFs and then check file size and potentially split
            content = []
            for pdf_path in downloaded_pdfs:
                if not isinstance(pdf_path, Exception):
                    logging.info(f"Processing PDF: {pdf_path}")
                    try:
                        # Open the PDF file
                        reader = PdfReader(pdf_path)
                        # Append each page from the current PDF to the content list
                        for page in reader.pages:
                            content.append((os.path.basename(pdf_path), page))
                        logging.info(f"Successfully processed and added pages from {pdf_path}")
                    except Exception as e:
                        logging.error(f"Failed to process PDF {pdf_path}: {e}")
                        self.bad_documents.append(pdf_path)
                    finally:
                        # Clean up: Remove the temporary downloaded PDF file
                        os.remove(pdf_path)
                        logging.info(f"Deleted temporary file: {pdf_path}")

            if content:
                pdf_strategy = PdfOutputStrategy()
                # Output the merged content using the PdfOutputStrategy
                pdf_strategy.output(content, self.output_path)
                # After successfully merging, check if the merged PDF needs to be split due to size constraints
                self.check_file_size_and_split()

    def calculate_pages_per_part(self, total_pages, total_pdf_size_bytes):
        """
        Calculates the number of pages each part should contain based on the maximum file size allowed,
        using an estimate of 3500 pages for a 100MB document.
        
        Args:
            total_pages (int): Total number of pages in the PDF.
            total_pdf_size_bytes (int): Total size of the PDF file in bytes.
        
        Returns:
            int: The number of pages each part should ideally contain.
        """
        # Estimate based on 3500 pages in a 100MB document
        estimated_page_size_bytes = (100 * 1024 * 1024) / 3500  # Convert 100MB to bytes and divide by 3500 pages
        
        # Calculate the number of pages per part based on the max file size allowed
        pages_per_part = max(1, int(self.max_file_size / estimated_page_size_bytes))
        
        return pages_per_part


    def check_file_size_and_split(self):
            file_size_bytes = os.path.getsize(self.output_path)
            if file_size_bytes > self.max_file_size:
                self.split_pdf()

    def split_pdf(self):
        """
        Splits the merged PDF file into multiple parts based on the maximum file size limit.

        The method reads the merged PDF file and calculates the number of pages per part based on the maximum file size limit.
        It then iterates over each page in the PDF, adding it to a new PDF writer.
        When the number of pages added reaches the calculated pages per part or the end of the PDF is reached, 
        it writes the current part to a new PDF file and resets the writer for the next part.
        Finally, it removes the original merged PDF file.

        Raises:
            FileNotFoundError: If the merged PDF file does not exist.
        """
        reader = PdfReader(self.output_path)
        total_pages = len(reader.pages)
        writer = PdfWriter()

        # Logic to calculate how many pages per part based on file size limit
        pages_per_part = self.calculate_pages_per_part(total_pages, self.max_file_size)
        part_number = 1

        for page_number, page in enumerate(reader.pages, start=1):
            writer.add_page(page)
            if page_number % pages_per_part == 0 or page_number == total_pages:
                part_output_path = f"{self.output_path[:-4]}_part_{part_number}.pdf"
                with open(part_output_path, 'wb') as part_file:
                    writer.write(part_file)
                writer = PdfWriter()  # Reset writer for next part
                part_number += 1
        os.remove(self.output_path)  # Remove the original merged file if split

            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge PDFs and optionally report bad documents in Markdown.")
    parser.add_argument("-f", "--folder", default=".", help="Folder to find local PDF files or save downloaded PDFs.")
    parser.add_argument("-o", "--output", default="merged.pdf", help="Filename for the output merged PDF.")
    parser.add_argument("-s", "--size", type=float, help="Maximum file size in MB for the merged PDF, triggering splitting if exceeded.")
    parser.add_argument("-l", "--list", dest="sources_file", help="Path to a file containing PDF URLs or file paths to merge.")
    parser.add_argument("-m", "--markdown", action="store_true", help="Output a Markdown report of bad documents.")

    args = parser.parse_args()

    tool = PDFMergerTool(folder=args.folder, output=args.output, max_file_size=args.size, sources_file=args.sources_file, output_markdown=args.markdown)
    
    # Run the asynchronous merge_pdfs method using asyncio.run() for Python 3.7+
    asyncio.run(tool.merge_pdfs())
