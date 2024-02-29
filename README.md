
# PDF Merger Tool

This PDF Merger Tool is an enhanced Python script capable of merging PDF files located in a specified directory or listed in a new-line delimited text file. The list can include both file paths and URLs to PDF documents. This tool now features logging for better tracking of its operations, especially useful when processing large files or numerous documents.

## Features

- **Merge Multiple PDFs:** Combine all PDF documents from a directory or a list into one.
- **Download and Merge PDFs from URLs:** Automatically download PDFs from provided URLs and merge them.
- **Custom Output Directory and Filename:** Specify the output directory and filename for the merged PDF.
- **File Size Check and Split:** If the merged PDF exceeds a specified size, it will be split into smaller parts.
- **Logging:** Detailed logging of the tool's operations, including file processing starts and ends.

## Requirements

- Python 3.x
- PyPDF2
- Requests

## Installation

Ensure Python 3.x is installed on your system. Then, install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Navigate to the directory containing the script in a terminal or command prompt.

### Basic Usage

To merge PDFs in the current directory:

```bash
python pdf_merger.py
```

### Custom Output Filename and Directory

Specify a custom name and directory for the output file:

```bash
python pdf_merger.py -o my_merged_document.pdf -f /path/to/output/folder
```

### Merging PDFs from a List

To merge PDFs specified in a text file (paths or URLs):

```bash
python pdf_merger.py -l path/to/pdf_list.txt
```

### Specifying Maximum File Size

To split the output into smaller files if it exceeds a certain size (in MB):

```bash
python pdf_merger.py -s 50
```

## Contributing

Contributions welcome. Please fork the repo, make your changes, and submit a pull request.

## License

MIT