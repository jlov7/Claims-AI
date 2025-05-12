# import psycopg2 # Add when DB connection is implemented
from PIL import Image  # Uncommented for Tesseract
import pytesseract  # Uncommented for Tesseract
import docx  # Uncommented for docx processing

# from PyPDF2 import PdfReader # Or other PDF library like pdfplumber
import argparse
import os
import json
from datetime import datetime
import pdfplumber  # Uncomment for PDF processing
import psycopg2  # Uncommented for DB interaction
from psycopg2 import sql  # For safe SQL query construction
from dotenv import load_dotenv  # For local .env loading
import hashlib

# Load environment variables from .env file, especially for local development
# Assumes .env is in the parent directory of scripts/
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

# Placeholder for database connection details (to be loaded from .env)
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")


def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        print(f"Successfully connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to PostgreSQL database '{DB_NAME}': {e}")
        print(
            "Please ensure the database is running and connection details in .env are correct."
        )
        print(
            f"Attempted connection with: DB: {DB_NAME}, User: {DB_USER}, Host: {DB_HOST}, Port: {DB_PORT}"
        )
        return None


def create_metadata_table_if_not_exists(conn):
    """Creates the document_metadata table if it doesn't already exist."""
    if not conn:
        print("No database connection, cannot create table.")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS document_metadata (
                id SERIAL PRIMARY KEY,
                original_filename VARCHAR(255) NOT NULL,
                processed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(100) NOT NULL, -- e.g., 'processed_pdf', 'failed_ocr', 'unsupported_type'
                processed_text_path VARCHAR(512), -- Path relative to a base, or full path if needed
                error_message TEXT,
                file_size_bytes BIGINT,
                sha256_hash VARCHAR(64), -- For duplicate detection/versioning
                CONSTRAINT unique_original_filename UNIQUE (original_filename)
            );
            """
            )
            conn.commit()
            print("'document_metadata' table checked/created successfully.")
    except psycopg2.Error as e:
        print(f"Error creating/checking 'document_metadata' table: {e}")
        conn.rollback()  # Rollback in case of partial table creation or other error


def update_metadata_in_db(
    conn,
    original_filename,
    processing_status,
    text_path=None,
    error_message=None,
    file_size=None,
    sha256_hash=None,
):
    """Stores or updates metadata in the PostgreSQL database."""
    if not conn:
        print(f"No database connection. Metadata for {original_filename} not updated.")
        return

    cleaned_text_path = text_path if text_path else None
    cleaned_error_message = error_message if error_message else None

    # Basic sanitization or truncation if error messages are very long
    if cleaned_error_message and len(cleaned_error_message) > 1000:
        cleaned_error_message = cleaned_error_message[:997] + "..."

    try:
        with conn.cursor() as cursor:
            query = sql.SQL(
                """
            INSERT INTO document_metadata (original_filename, status, processed_text_path, error_message, file_size_bytes, sha256_hash, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (original_filename) DO UPDATE SET
                status = EXCLUDED.status,
                processed_text_path = EXCLUDED.processed_text_path,
                error_message = EXCLUDED.error_message,
                file_size_bytes = EXCLUDED.file_size_bytes,
                sha256_hash = EXCLUDED.sha256_hash,
                processed_at = EXCLUDED.processed_at;
            """
            )
            cursor.execute(
                query,
                (
                    original_filename,
                    processing_status,
                    cleaned_text_path,
                    cleaned_error_message,
                    file_size,
                    sha256_hash,
                    datetime.now(),
                ),
            )
            conn.commit()
            print(
                f"Metadata for '{original_filename}' successfully saved to database. Status: {processing_status}"
            )
    except psycopg2.Error as e:
        print(f"Database error updating metadata for {original_filename}: {e}")
        conn.rollback()
    except Exception as ex:
        print(
            f"An unexpected error occurred during DB update for {original_filename}: {ex}"
        )
        if conn:
            conn.rollback()


def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file, trying direct extraction then OCR."""
    extracted_text = ""
    try:
        # Attempt 1: Direct text extraction with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"

        if (
            extracted_text.strip() and len(extracted_text.strip()) > 100
        ):  # Arbitrary threshold for meaningful text
            print(f"Successfully extracted text from PDF {file_path} using pdfplumber.")
            return extracted_text.strip()
        else:
            print(
                f"Direct text extraction from PDF {file_path} yielded little or no text. Attempting OCR..."
            )
            # Fallback to OCR if direct extraction yields little text
            extracted_text = ""  # Reset for OCR
            # This requires pdf2image or similar to convert PDF pages to images for Tesseract
            # For simplicity in this step, let's assume Tesseract can handle PDF paths directly for OCR
            # (though it might be less reliable or need specific Tesseract configurations/versions).
            # A more robust solution would iterate through pages, convert each to an image, then OCR.
            try:
                # Note: Tesseract direct PDF processing can be slow and memory intensive for large PDFs.
                # It might also depend on how Tesseract was compiled (e.g., with PDF support).
                extracted_text = pytesseract.image_to_string(
                    file_path, timeout=300
                )  # Add timeout
            except (
                RuntimeError
            ) as re:  # Handle Tesseract timeout or other runtime errors
                print(
                    f"Tesseract OCR on PDF {file_path} failed or timed out: {re}. Trying page by page image conversion if possible."
                )
                # Placeholder for more robust page-by-page OCR if direct Tesseract on PDF fails.
                # This would involve a library like `pdf2image` to convert pages to PIL Images.
                # from pdf2image import convert_from_path
                # try:
                #     images = convert_from_path(file_path)
                #     ocr_texts = []
                #     for i, img_page in enumerate(images):
                #         print(f"OCR-ing page {i+1} of PDF {file_path}")
                #         ocr_texts.append(pytesseract.image_to_string(img_page))
                #     extracted_text = "\n".join(ocr_texts)
                # except Exception as e_conv:
                #     print(f"Could not convert PDF {file_path} to images for OCR: {e_conv}")
                #     extracted_text = "" # Ensure it's empty if conversion fails
                extracted_text = ""  # Fallback if direct tesseract on PDF fails and page-by-page not implemented here

            if extracted_text.strip():
                print(
                    f"Successfully extracted text from PDF {file_path} using Tesseract OCR."
                )
                return extracted_text.strip()
            else:
                print(
                    f"OCR attempt on PDF {file_path} also yielded no significant text."
                )
                return None

    except Exception as e:
        print(f"Error processing PDF {file_path}: {e}")
        return None


def extract_text_from_tiff(file_path):
    """Extracts text from a TIFF file using Tesseract."""
    try:
        # You might need to specify the Tesseract command path if it's not in your system's PATH
        # For example, on macOS if installed via Homebrew:
        # pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract' # Or /opt/homebrew/bin/tesseract for Apple Silicon
        text = pytesseract.image_to_string(Image.open(file_path))
        if not text.strip():
            print(
                f"Warning: Tesseract extracted no text or only whitespace from TIFF {file_path}."
            )
            # Consider if this should be an error or just an empty result
            return None  # Or empty string
        return text
    except pytesseract.TesseractNotFoundError:
        print(
            "Error: Tesseract is not installed or not found in your PATH. Please install Tesseract."
        )
        # This is a critical error for TIFF/image processing, might want to raise or handle differently
        return None
    except Exception as e:
        print(f"Error extracting text from TIFF {file_path} with Tesseract: {e}")
        return None


def extract_text_from_docx(file_path):
    """Extracts text from a DOCX file."""
    try:
        doc_obj = docx.Document(file_path)
        full_text = []
        for para in doc_obj.paragraphs:
            full_text.append(para.text)
        extracted_content = "\n".join(full_text)
        if not extracted_content.strip():
            print(
                f"Warning: DOCX file {file_path} seems to be empty or contains only whitespace."
            )
            return None
        return extracted_content
    except Exception as e:
        print(f"Error extracting text from DOCX {file_path}: {e}")
        # from docx.opc.exceptions import PackageNotFoundError # Example of specific exception
        # if isinstance(e, PackageNotFoundError):
        #     print(f"Error: DOCX file {file_path} is not a valid DOCX file or is corrupted.")
        return None


def calculate_sha256(file_path):
    """Calculates SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        print(f"Error reading file {file_path} for hashing: {e}")
        return None


def process_file(file_path, output_dir, db_conn):
    """Processes a single file: extracts text, saves it, and updates metadata."""
    original_filename = os.path.basename(file_path)
    file_ext = os.path.splitext(original_filename)[1].lower()
    extracted_text = None
    status = "unsupported_initial"
    error_detail = None
    file_size = None
    file_hash = None

    try:
        file_size = os.path.getsize(file_path)
        file_hash = calculate_sha256(file_path)
    except OSError as e:
        print(f"Error getting file metadata for {original_filename}: {e}")
        status = "error_file_access"
        error_detail = f"Could not access file metadata: {str(e)}"
        if db_conn:
            update_metadata_in_db(
                db_conn, original_filename, status, error_message=error_detail
            )
        return

    print(
        f"Processing file: {original_filename} (Size: {file_size}B, SHA256: {file_hash[:8]}...)"
    )

    if file_ext == ".pdf":
        extracted_text = extract_text_from_pdf(file_path)
        status = "processed_pdf" if extracted_text else "failed_pdf_extraction"
        if not extracted_text:
            error_detail = "PDF extraction returned no text or failed."
    elif file_ext in [".tiff", ".tif"]:
        extracted_text = extract_text_from_tiff(file_path)
        status = "processed_tiff" if extracted_text else "failed_tiff_extraction"
        if not extracted_text:
            error_detail = "TIFF extraction returned no text or failed."
    elif file_ext == ".docx":
        extracted_text = extract_text_from_docx(file_path)
        status = "processed_docx" if extracted_text else "failed_docx_extraction"
        if not extracted_text:
            error_detail = "DOCX extraction returned no text or failed."
    else:
        print(f"Unsupported file type: {file_ext} for file {original_filename}")
        status = "unsupported_type"
        error_detail = f"Unsupported file type: {file_ext}"
        if db_conn:
            update_metadata_in_db(
                db_conn,
                original_filename,
                status,
                error_message=error_detail,
                file_size=file_size,
                sha256_hash=file_hash,
            )
        return

    output_json_path = None
    if extracted_text:
        output_filename_base = os.path.splitext(original_filename)[0]
        output_json_filename = f"{output_filename_base}.json"
        output_json_path = os.path.join(output_dir, output_json_filename)
        output_data = {
            "original_filename": original_filename,
            "extraction_timestamp": datetime.now().isoformat(),
            "source_file_extension": file_ext,
            "file_size_bytes": file_size,
            "sha256_hash": file_hash,
            "content": extracted_text,
        }
        try:
            with open(output_json_path, "w", encoding="utf-8") as f_json:
                json.dump(output_data, f_json, ensure_ascii=False, indent=4)
            print(f"Successfully saved extracted text to: {output_json_path}")
            # Status here is already set (e.g. processed_pdf)
        except IOError as e:
            print(f"Error saving JSON to {output_json_path}: {e}")
            status = f"failed_saving_output ({status})"  # Append to original status
            error_detail = f"IOError saving output: {str(e)}"
            output_json_path = None  # Ensure path is None if saving failed
    else:
        # error_detail is already set by extraction functions if they fail
        # status is also set (e.g., failed_pdf_extraction)
        print(
            f"No text extracted from {original_filename} or extraction failed. Status: {status}"
        )

    if db_conn:
        update_metadata_in_db(
            db_conn,
            original_filename,
            status,
            text_path=output_json_path,
            error_message=error_detail,
            file_size=file_size,
            sha256_hash=file_hash,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from documents (PDF, TIFF, DOCX) and store metadata in Postgres."
    )
    parser.add_argument(
        "--src", required=True, help="Source directory containing raw documents."
    )
    parser.add_argument(
        "--out", required=True, help="Output directory for processed text (JSON files)."
    )
    args = parser.parse_args()

    src_dir = args.src
    out_dir = args.out

    if not os.path.isdir(src_dir):
        print(f"Error: Source directory '{src_dir}' not found.")
        return
    if not os.path.isdir(out_dir):
        print(f"Output directory '{out_dir}' not found. Creating it...")
        os.makedirs(out_dir, exist_ok=True)

    db_conn = get_db_connection()  # Try to connect

    if not db_conn:
        print(
            "CRITICAL: Could not connect to the database. Metadata will not be stored. Exiting script."
        )
        return  # Exit if no DB connection, as per requirements for metadata storage

    create_metadata_table_if_not_exists(db_conn)  # Ensure table exists

    print(f"Starting text extraction from '{src_dir}' to '{out_dir}'...")

    for item in os.listdir(src_dir):
        item_path = os.path.join(src_dir, item)
        if os.path.isfile(item_path):
            process_file(item_path, out_dir, db_conn)
        else:
            print(f"Skipping directory: {item}")

    print("Text extraction process completed.")
    if db_conn:
        db_conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    # For environment variables to be available if script is run directly during dev:
    # from dotenv import load_dotenv
    # load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
    # print(f"DB_HOST from env: {os.getenv('POSTGRES_HOST')}") # For testing .env loading
    main()
