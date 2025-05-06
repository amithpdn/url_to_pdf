# Web Page to PDF Converter

A robust Python utility for saving web pages as PDF files with enhanced reliability and customization options.

## Features

- **Batch Processing**: Process multiple URLs in configurable batches
- **Timeout Handling**: Automatically detect and handle hanging processes
- **Retry Logic**: Configurable retries with progressive backoff
- **User-Agent Rotation**: Rotate through multiple user-agents to avoid blocking
- **Error Logging**: Detailed logging and tracking of failed URLs
- **Customizable Delays**: Random delays between requests to be gentle on servers
- **Auto-Resume**: Skip already downloaded files

## Requirements

- Python 3.11+
- wkhtmltopdf executable (<https://wkhtmltopdf.org/downloads.html>)

## Installation

1. Clone or download this repository
2. Install the required Python packages:
   - Option1: Using `pip`

   ```bash
   pip install pdfkit
   ```

   - Option2: Using `uv`

   ```bash
   uv sync
   ```

   > Note: If you are using `uv`, ensure you have it installed and set up correctly. You can find more information on [uv's official documentation](https://docs.astral.sh/uv/) or [uv_usage.md](./uv_usage.md).

3. Install wkhtmltopdf:
   - Download from <https://wkhtmltopdf.org/downloads.html>
   - Install the package for your operating system
   - Note the path to the executable (e.g., `C:\wkhtmltopdf\bin\wkhtmltopdf.exe` on Windows)

## Usage

### Basic Usage

```bash
python save_page_enhanced.py --input urls.txt --output ./pdfs
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input`, `-i` | Path to text file with URLs (one per line) | None |
| `--output`, `-o` | Output directory for PDFs | `./pdfs` |
| `--wkhtmltopdf` | Path to wkhtmltopdf executable | `C:\wkhtmltopdf\bin\wkhtmltopdf.exe` |
| `--batch-size` | Number of URLs to process in each batch | 10 |
| `--min-delay` | Minimum delay between requests (seconds) | 2.0 |
| `--max-delay` | Maximum delay between requests (seconds) | 5.0 |
| `--max-retries` | Maximum number of retry attempts | 3 |
| `--timeout` | Timeout for each conversion (seconds) | 60 |
| `--urls` | Specify URLs directly in command line | None |

### Examples

#### Process URLs from a File

```bash
python save_page_enhanced.py --input urls.txt --output ./pdfs
```

#### Specify URLs Directly

```bash
python save_page_enhanced.py --urls https://example.com https://another-example.com
```

#### Customize Processing Parameters

```bash
python save_page_enhanced.py --input urls.txt --batch-size 5 --min-delay 3 --max-delay 8 --timeout 30
```

#### Retry Failed URLs

```bash
python save_page_enhanced.py --input ./pdfs/failed_urls.txt --output ./pdfs --timeout 120
```

## Input File Format

The input file should contain one URL per line:

```
https://example.com
https://another-example.com
https://yet-another-example.com
```

## Output

- PDFs will be saved to the specified output directory
- Filenames are derived from the last part of the URL
- A `failed_urls.txt` file will be created in the output directory listing any URLs that couldn't be converted

## Logging

The script logs detailed information about the conversion process:

- Console output for real-time monitoring
- Log file in the `logs` directory for later reference

## Troubleshooting

### Common Issues

1. **Timeouts**: If many URLs are timing out, try increasing the `--timeout` value.
2. **Blocked by Websites**: Some websites may block automated access. Try using a larger `--min-delay` value.
3. **wkhtmltopdf Errors**: Ensure you have the correct path to the wkhtmltopdf executable.
4. **Memory Issues**: If processing many URLs, try reducing the `--batch-size` value.

### Handling Failed URLs

After the script runs, check the `failed_urls.txt` file in the output directory for any failed URLs. You can retry these with adjusted parameters:

```bash
python save_page_enhanced.py --input ./pdfs/failed_urls.txt --output ./pdfs --timeout 120 --max-retries 5
```

## Advanced Configurations

### Custom User-Agents

The script rotates through several common user-agents by default. You can modify the `USER_AGENTS` list in the script to add or remove user-agents.

### Working with Large URL Lists

For very large URL lists (thousands of URLs), it's recommended to:

1. Use a smaller batch size: `--batch-size 5`
2. Increase delays between batches: `--min-delay 5 --max-delay 10`
3. Run the script in multiple sessions, splitting the URL list into smaller files

## License

This script is provided under the [MIT License](./license.md). Feel free to modify and distribute it as needed.

## Acknowledgments

- Uses the excellent [pdfkit](https://github.com/JazzCore/python-pdfkit) library
- Powered by [wkhtmltopdf](https://wkhtmltopdf.org/) for HTML to PDF conversion
