import pdfkit
import os
import time
import logging
import random
import argparse
from urllib.parse import urlparse

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging to write to a file in logs directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'url_to_pdf.log')),
        logging.StreamHandler()  # Keep console output too
    ]
)
logger = logging.getLogger(__name__)

# Default wkhtmltopdf path - update this for your system
DEFAULT_WKHTMLTOPDF_PATH = r"C:\wkhtmltopdf\bin\wkhtmltopdf.exe"

# List of common user agents to rotate through
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def get_filename_from_url(url):
    """Extract a sensible filename from URL"""
    parsed_url = urlparse(url)
    path = parsed_url.path.rstrip('/')
    
    # If path is empty, use the domain name as the filename
    if not path or path == '/':
        filename = parsed_url.netloc
    else:
        # Extract the last part of the path
        filename = path.split('/')[-1]
    
    # Remove any query parameters
    filename = filename.split('?')[0]
    
    # Remove any illegal characters
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # Add .pdf extension if not present
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    
    return filename

def save_webpage_as_pdf(url, output_path, wkhtmltopdf_path, max_retries=3, retry_delay=5, timeout=30):
    """Save a single webpage as PDF with retry logic and timeout"""
    import subprocess
    
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    options = {
        'javascript-delay': 5000,  # Wait for JavaScript to execute (5 seconds)
        'no-stop-slow-scripts': None,  # Don't stop slow running scripts
        'custom-header': [
            ('User-Agent', get_random_user_agent())
        ],
        'custom-header-propagation': None,  # Propagate headers to all requests
        'quiet': None  # Reduce terminal output from wkhtmltopdf
    }
    
    def kill_wkhtmltopdf():
        """Kill any running wkhtmltopdf processes"""
        try:
            if os.name == 'nt':  # Windows
                subprocess.call(['taskkill', '/f', '/im', 'wkhtmltopdf.exe'], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:  # Unix/Linux/MacOS
                subprocess.call(['pkill', '-f', 'wkhtmltopdf'], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Killed hanging wkhtmltopdf process")
        except Exception as e:
            logger.warning(f"Failed to kill wkhtmltopdf process: {e}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Saving: {url} as {output_path} (Attempt {attempt + 1}/{max_retries})")
            
            # Use subprocess with timeout instead of threading
            # This avoids the thread exception issue
            if os.name == 'nt':  # Windows
                cmd = [
                    wkhtmltopdf_path,
                    '--javascript-delay', '5000',
                    '--no-stop-slow-scripts',
                    '--custom-header', 'User-Agent', get_random_user_agent(),
                    '--custom-header-propagation',
                    '--quiet',
                    url,
                    output_path
                ]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    if process.returncode == 0:
                        logger.info(f"Successfully saved: {url} as {output_path}")
                        return True
                    else:
                        error_msg = stderr.decode('utf-8', errors='ignore')
                        raise Exception(f"wkhtmltopdf failed with error: {error_msg}")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Conversion timed out after {timeout} seconds for {url}")
                    process.kill()
                    kill_wkhtmltopdf()  # Kill any other hanging processes
                    process.communicate()  # Clean up
                    raise Exception("Conversion timed out")
            else:
                # Fall back to pdfkit for non-Windows platforms
                # We'll use a simple signal-based timeout for Unix systems
                import signal
                
                class TimeoutException(Exception):
                    pass
                
                def timeout_handler(signum, frame):
                    kill_wkhtmltopdf()
                    raise TimeoutException("Timed out")
                
                # Set the timeout handler
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
                
                try:
                    pdfkit.from_url(url, output_path, options=options, configuration=config)
                    signal.alarm(0)  # Disable the alarm
                    logger.info(f"Successfully saved: {url} as {output_path}")
                    return True
                except TimeoutException:
                    logger.warning(f"Conversion timed out after {timeout} seconds for {url}")
                    raise Exception("Conversion timed out")
                finally:
                    signal.signal(signal.SIGALRM, old_handler)  # Restore the old handler
                    signal.alarm(0)  # Disable the alarm
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
            
            # Make sure no wkhtmltopdf processes are hanging
            kill_wkhtmltopdf()
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)  # Progressive backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    logger.error(f"Failed to save {url} after {max_retries} attempts")
    return False

def save_webpages_as_pdfs(url_list, output_folder, wkhtmltopdf_path, batch_size=10, 
                          min_delay=2, max_delay=5, max_retries=3, timeout=60):
    """
    Save multiple webpages as PDFs with improved features:
    - Process URLs in batches to avoid memory issues
    - Variable wait times between requests
    - Retry logic for failed downloads
    - Timeout for hanging conversions
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # Create a file to track failed URLs
    failed_urls_path = os.path.join(output_folder, 'failed_urls.txt')
    success_count = 0
    failure_count = 0
    
    # Process URLs in batches
    for batch_idx in range(0, len(url_list), batch_size):
        batch = url_list[batch_idx:batch_idx + batch_size]
        logger.info(f"Processing batch {batch_idx // batch_size + 1}/{(len(url_list) + batch_size - 1) // batch_size}")
        
        for url in batch:
            filename = get_filename_from_url(url)
            output_path = os.path.join(output_folder, filename)
            
            # Skip if file already exists
            if os.path.exists(output_path):
                logger.info(f"Skipping {url} - file already exists at {output_path}")
                continue
            
            result = save_webpage_as_pdf(url, output_path, wkhtmltopdf_path, max_retries, 
                                         retry_delay=5, timeout=timeout)
            
            if result:
                success_count += 1
            else:
                failure_count += 1
                # Log failed URL to file
                with open(failed_urls_path, 'a') as f:
                    f.write(f"{url}\n")
            
            # Add random delay between requests
            if url != batch[-1]:  # No need to wait after the last URL in the batch
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)
        
        # Add a longer delay between batches
        if batch_idx + batch_size < len(url_list):
            batch_delay = random.uniform(max_delay, max_delay * 2)
            logger.info(f"Batch complete. Waiting {batch_delay:.2f} seconds before next batch...")
            time.sleep(batch_delay)
    
    logger.info(f"PDF conversion complete! Success: {success_count}, Failures: {failure_count}")
    if failure_count > 0:
        logger.info(f"Failed URLs have been saved to {failed_urls_path}")
    
    return success_count, failure_count

def main():
    parser = argparse.ArgumentParser(description='Save webpages as PDFs')
    parser.add_argument('--input', '-i', 
                        help='Path to a text file containing URLs (one per line)')
    parser.add_argument('--output', '-o', default='./pdfs',
                        help='Output directory for PDFs (default: ./pdfs)')
    parser.add_argument('--wkhtmltopdf', default=DEFAULT_WKHTMLTOPDF_PATH,
                        help=f'Path to wkhtmltopdf executable (default: {DEFAULT_WKHTMLTOPDF_PATH})')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of URLs to process in each batch (default: 10)')
    parser.add_argument('--min-delay', type=float, default=2.0,
                        help='Minimum delay between requests in seconds (default: 2.0)')
    parser.add_argument('--max-delay', type=float, default=5.0,
                        help='Maximum delay between requests in seconds (default: 5.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Maximum number of retry attempts for failed downloads (default: 3)')
    parser.add_argument('--timeout', type=int, default=60,
                        help='Timeout in seconds for each PDF conversion (default: 60)')
    parser.add_argument('--urls', nargs='+',
                        help='One or more URLs to convert (alternative to --input)')
    
    args = parser.parse_args()
    
    # Validate input sources
    if not args.input and not args.urls:
        parser.error("Either --input file or --urls must be provided")
    
    # Get URLs from input file or command line arguments
    if args.input:
        try:
            with open(args.input, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Failed to read input file: {e}")
            return
    else:
        urls = args.urls
    
    logger.info(f"Starting PDF conversion for {len(urls)} URLs")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"wkhtmltopdf path: {args.wkhtmltopdf}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Delay range: {args.min_delay}-{args.max_delay} seconds")
    logger.info(f"Max retries: {args.max_retries}")
    logger.info(f"Conversion timeout: {args.timeout} seconds")
    logger.info('*********************************************************')
    
    save_webpages_as_pdfs(
        urls, 
        args.output, 
        args.wkhtmltopdf,
        args.batch_size,
        args.min_delay,
        args.max_delay,
        args.max_retries,
        args.timeout
    )

# Example usage
if __name__ == "__main__":
    main()