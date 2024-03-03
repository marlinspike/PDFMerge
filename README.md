# PDF Merger Tool

This PDF Merger Tool is a comprehensive Python utility designed for merging PDF files either from a specified directory or listed in a newline-separated text file. It supports merging PDFs directly from URLs, making it a versatile tool for various PDF processing needs. It also supports merging downloaded PDFs into Markdown files for plain-text lookups. You can specify the Max file size of output files, and the tool will automatically span multiple PDFs or Markdown files, within the specified limit.

## Features

- **Merge Multiple PDFs:** Seamlessly combine PDF documents from a directory or a list into a single PDF or Markdown file.
- **Download and Merge PDFs from URLs:** Automatically fetches and merges PDFs from given URLs, so you can process any number of PDFs at one time.
- **File Size Check and Split:** Automatically splits the merged PDF into smaller parts if it exceeds a predefined size limit.
- **Custom Output Directory and Filename:** Users can define the output directory and filename for the merged PDF.
- **Markdown Reporting:** Optionally generates a Markdown report of the processed documents, including a list of any documents that could not be processed.

## Requirements

- Python 3.x
- PyPDF2
- Requests
- Fitz (PyMuPDF)

## Installation

First, ensure Python 3.x is installed on your system. Then, install the necessary dependencies:

```bash
pip install -r requirements.txt


## Usage

Navigate to the directory containing the script in a terminal or command prompt.

### Basic Usage

To merge PDFs in the current directory:

```bash
python pdfmerge.py
```

### Custom Output Filename and Directory

Specify a custom name and directory for the output file:

```bash
python pdfmerge.py -o my_merged_document.pdf -f /path/to/output/folder
```

### Merging PDFs from a List

To merge PDFs specified in a text file (paths or URLs):

```bash
python pdfmerge.py -l path/to/pdf_list.md
```

### Specifying Maximum File Size

To split the output into smaller files if it exceeds a certain size (in MB):

```bash
python pdfmerge.py -s 50
```

### Markdown output

Generate a Markdown document containing all the data from the downloaded PDFs:
```bash
python pdfmerge.py -m
```

## Contributing

Contributions welcome. Please fork the repo, make your changes, and submit a pull request.

## License

MIT