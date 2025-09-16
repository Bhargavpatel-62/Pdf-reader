import streamlit as st
import zipfile
import re
import pandas as pd
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor, as_completed

# ----------------------------
# Streamlit config
# ----------------------------
st.set_page_config(page_title="PDF ID Extractor", layout="wide")
st.title("📂 PDF ID Extractor (Fast & Optimized Version)")

uploaded_files = st.file_uploader(
    "Upload PDFs or ZIP files (multiple allowed)",
    type=["pdf", "zip"],
    accept_multiple_files=True
)

# ----------------------------
# Function to process a single PDF
# ----------------------------
def process_pdf(file_name, file_obj):
    try:
        reader = PdfReader(file_obj)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        match = re.search(r"\b\d{18,22}\b", text)
        extracted_id = match.group(0) if match else None
        return {"File": file_name, "Extracted_ID": extracted_id, "Error": None}
    except Exception as e:
        return {"File": file_name, "Extracted_ID": None, "Error": str(e)}

# ----------------------------
# Function to process ZIP
# ----------------------------
def process_zip(file_obj):
    results = []
    try:
        with zipfile.ZipFile(file_obj) as z:
            for file_info in z.infolist():
                if file_info.filename.lower().endswith(".pdf"):
                    with z.open(file_info) as pdf_file:
                        results.append(process_pdf(file_info.filename, pdf_file))
    except Exception as e:
        results.append({"File": "ZIP_Error", "Extracted_ID": None, "Error": str(e)})
    return results

# ----------------------------
# Main processing
# ----------------------------
if uploaded_files:
    results = []

    progress_text = st.empty()
    progress_bar = st.progress(0)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        total_files = len(uploaded_files)
        for file in uploaded_files:
            if file.name.lower().endswith(".pdf"):
                futures.append(executor.submit(process_pdf, file.name, file))
            elif file.name.lower().endswith(".zip"):
                futures.append(executor.submit(process_zip, file))

        for i, future in enumerate(as_completed(futures)):
            res = future.result()
            if isinstance(res, list):
                results.extend(res)
            else:
                results.append(res)

            # Update progress bar
            progress_bar.progress((i + 1) / total_files)
            progress_text.text(f"Processing file {i+1}/{total_files}...")

    # ----------------------------
    # Prepare DataFrame
    # ----------------------------
    if results:
        df = pd.DataFrame(results)
        df["Status"] = df["Extracted_ID"].duplicated(keep=False).map(
            {True: "Duplicate", False: "Unique"}
        )

        st.success(f"✅ Processed {len(df)} files successfully!")
        st.dataframe(df, use_container_width=True)

        # Show errors if any
        errors = df[df["Error"].notna()]
        if not errors.empty:
            st.error("⚠️ Some files could not be processed:")
            st.table(errors[["File", "Error"]])

        # Save Excel
        output_file = "extracted_ids.xlsx"
        df.to_excel(output_file, index=False)

        with open(output_file, "rb") as f:
            st.download_button(
                label="⬇️ Download Excel",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
