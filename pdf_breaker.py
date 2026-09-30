from pathlib import Path
import pymupdf
import re


# ============================================================
# CONFIGURATION
# ============================================================

PDF_FILE = "input_pdf.pdf"


# ============================================================
# OCR PAGE
# ============================================================

def get_page_text_with_ocr(page):
    """
    Run OCR on the page and return recognized text.
    """

    try:

        text_page = page.get_textpage_ocr(
            language="eng",
            dpi=200,
            full=True
        )

        text = page.get_text(
            "text",
            textpage=text_page
        )

        return text

    except Exception as e:

        print()
        print(
            f"OCR ERROR on page {page.number + 1}:"
        )

        print(e)

        return ""


# ============================================================
# DETECT NEW INVOICE
# ============================================================

def is_invoice_start(text):
    """
    Determines whether OCR text indicates that this page
    is the first page of an invoice.
    """

    if not text:
        return False

    # Normalize spaces/newlines
    normalized = re.sub(
        r"\s+",
        " ",
        text
    ).lower()

    # ========================================================
    # Strong invoice-start patterns
    # ========================================================

    patterns = [

        # Invoice #
        r"\binvoice\s*#",

        # Invoice No
        # Invoice No.
        r"\binvoice\s+no\.?",

        # Invoice Number
        r"\binvoice\s+number",

        # Invoice: 1234
        r"\binvoice\s*:",

        # Invoice Report
        r"\binvoice\s+report\b",

        # Invoice For...
        r"\binvoice\s+for\b",
    ]

    for pattern in patterns:

        if re.search(
            pattern,
            normalized,
            re.IGNORECASE
        ):
            return True

    # ========================================================
    # Fallback
    #
    # If OCR finds Invoice plus common first-page fields,
    # it is probably an invoice start.
    # ========================================================

    if "invoice" in normalized:

        supporting_words = [
            "bill to",
            "invoice date",
            "invoice #",
            "invoice no",
            "invoice number",
            "balance due",
            "amount due",
            "billing period",
            "terms",
        ]

        matches = sum(
            word in normalized
            for word in supporting_words
        )

        if matches >= 1:
            return True

    return False


# ============================================================
# SPLIT PDF
# ============================================================

def split_invoices(pdf_file):

    pdf_path = Path(pdf_file)

    # ========================================================
    # CHECK FILE
    # ========================================================

    if not pdf_path.exists():

        print()
        print("ERROR: PDF not found:")
        print(pdf_path)

        return

    # ========================================================
    # OPEN PDF
    # ========================================================

    pdf = pymupdf.open(pdf_path)

    total_pages = len(pdf)

    print()
    print("=" * 70)
    print("PDF PROCESSING STARTED")
    print("=" * 70)

    print(f"File        : {pdf_path.name}")
    print(f"Total pages : {total_pages}")

    print()
    print("=" * 70)
    print("RUNNING OCR")
    print("=" * 70)
    print()

    invoice_start_pages = []


    # ========================================================
    # SCAN EVERY PAGE
    # ========================================================

    for page_number in range(total_pages):

        page = pdf[page_number]

        print(
            f"OCR Page {page_number + 1:03d}/{total_pages}...",
            end=" "
        )

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        text = get_page_text_with_ocr(page)

        # ----------------------------------------------------
        # Clean preview for debugging
        # ----------------------------------------------------

        preview = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        # ----------------------------------------------------
        # Detect invoice
        # ----------------------------------------------------

        invoice_start = is_invoice_start(text)

        if invoice_start:

            invoice_start_pages.append(
                page_number
            )

            print("NEW INVOICE")

            print(
                f"    OCR: {preview[:200]}"
            )

        else:

            print("continuation/other")


    # ========================================================
    # SHOW DETECTED INVOICES
    # ========================================================

    print()
    print("=" * 70)
    print("INVOICE START PAGES")
    print("=" * 70)

    readable_pages = [
        page + 1
        for page in invoice_start_pages
    ]

    print(readable_pages)


    # ========================================================
    # NOTHING FOUND
    # ========================================================

    if not invoice_start_pages:

        print()
        print("No invoices detected using OCR.")
        print()
        print(
            "Check the OCR output above to see what "
            "Tesseract recognized."
        )

        pdf.close()

        return


    # ========================================================
    # CREATE PDFs
    # ========================================================

    print()
    print("=" * 70)
    print("CREATING INVOICE PDFs")
    print("=" * 70)
    print()

    for index, start_page in enumerate(
        invoice_start_pages
    ):

        # ----------------------------------------------------
        # Calculate ending page
        # ----------------------------------------------------

        if index + 1 < len(invoice_start_pages):

            end_page = (
                invoice_start_pages[index + 1]
                - 1
            )

        else:

            end_page = total_pages - 1


        # ----------------------------------------------------
        # Create PDF
        # ----------------------------------------------------

        output_pdf = pymupdf.open()

        # IMPORTANT:
        #
        # We are copying ORIGINAL PDF pages.
        # OCR is only used to find invoice boundaries.
        #
        # Therefore original PDF quality is preserved.

        output_pdf.insert_pdf(
            pdf,
            from_page=start_page,
            to_page=end_page
        )


        # ----------------------------------------------------
        # Filename
        # ----------------------------------------------------

        filename = (
            f"Invoice_{index + 1:03d}.pdf"
        )

        output_path = (
            pdf_path.parent / filename
        )


        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        output_pdf.save(
            output_path
        )

        output_pdf.close()


        print(
            f"Created: {filename:<20} "
            f"Pages {start_page + 1}-{end_page + 1}"
        )


    # ========================================================
    # FINISH
    # ========================================================

    pdf.close()

    print()
    print("=" * 70)
    print("PROCESSING COMPLETED")
    print("=" * 70)

    print()
    print(
        f"Total invoices created: "
        f"{len(invoice_start_pages)}"
    )

    print()
    print("Files saved in:")
    print(pdf_path.parent)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    split_invoices(PDF_FILE)