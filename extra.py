import streamlit as st
import zipfile
import re
import pandas as pd
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

# ----------------------------
# Streamlit config
# ----------------------------
st.set_page_config(page_title="PDF ID Extractor", layout="wide")
st.title("📂 PDF ID Extractor (Fast & Optimized Version)")

# ----------------------------
# Session state
# ----------------------------
if "uploads" not in st.session_state:
    # list of {name: str, bytes: bytes}
    st.session_state.uploads = []
if "results_df" not in st.session_state:
    st.session_state.results_df = None
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

uploaded_files = st.file_uploader(
    "Upload PDFs or ZIP files (multiple allowed)",
    type=["pdf", "zip"],
    accept_multiple_files=True,
    disabled=st.session_state.is_processing,
    help="Files persist until you click Clear all."
)

# Store newly uploaded files into session_state (avoid duplicates by name+size)
if uploaded_files:
    existing_keys = {f["name"] + str(len(f["bytes"])) for f in st.session_state.uploads}
    for f in uploaded_files:
        try:
            data = f.getbuffer().tobytes()
        except Exception:
            # fallback
            data = f.read()
        key = f.name + str(len(data))
        if key not in existing_keys:
            st.session_state.uploads.append({"name": f.name, "bytes": data})
            existing_keys.add(key)

# ----------------------------
# Function to process a single PDF
# ----------------------------
def process_pdf(file_name, file_obj):
    try:
        reader = PdfReader(file_obj)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        pattern = build_id_pattern(min_len, max_len, include_symbols)
        match = re.search(pattern, text, flags=re.IGNORECASE)
        extracted_id = match.group(0).upper() if match else None
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
# Controls
# ----------------------------
left, mid, right = st.columns([2, 2, 2])
with left:
    st.write(f"Attached files: {len(st.session_state.uploads)}")
    if st.session_state.uploads:
        st.caption("Files are kept until you click Clear all.")
        st.dataframe(
            pd.DataFrame({"File": [f["name"] for f in st.session_state.uploads]}),
            use_container_width=True,
            height=min(240, 35 * max(1, len(st.session_state.uploads)))
        )
with mid:
    run_clicked = st.button(
        "▶️ Run",
        type="primary",
        disabled=st.session_state.is_processing or not st.session_state.uploads,
        help="Process the attached files"
    )
with right:
    clear_clicked = st.button(
        "🧹 Clear all",
        disabled=st.session_state.is_processing and False,
        help="Remove all attached files and results"
    )

if clear_clicked:
    st.session_state.uploads = []
    st.session_state.results_df = None
    st.rerun()

# ----------------------------
# Extraction settings
# ----------------------------
s1, s2, s3 = st.columns(3)
with s1:
    min_len = st.number_input("Min ID length", min_value=1, max_value=1000, value=8, step=1)
with s2:
    max_len = st.number_input("Max ID length (0 = unlimited)", min_value=0, max_value=10000, value=0, step=1)
with s3:
    include_symbols = st.checkbox("Allow '_' and '-'", value=False)

def build_id_pattern(min_len, max_len, include_symbols):
    char_class = r"[A-Za-z0-9_-]" if include_symbols else r"[A-Za-z0-9]"
    if max_len and max_len >= min_len:
        quant = f"{{{min_len},{max_len}}}"
    else:
        quant = f"{{{min_len},}}"
    return rf"\b{char_class}{quant}\b"
    
# ----------------------------
# Processing on demand
# ----------------------------
if run_clicked and st.session_state.uploads:
    st.session_state.is_processing = True
    results = []

    progress_text = st.empty()
    progress_bar = st.progress(0)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        total_files = len(st.session_state.uploads)
        for file_rec in st.session_state.uploads:
            name = file_rec["name"]
            data = file_rec["bytes"]
            if name.lower().endswith(".pdf"):
                futures.append(executor.submit(process_pdf, name, BytesIO(data)))
            elif name.lower().endswith(".zip"):
                futures.append(executor.submit(process_zip, BytesIO(data)))

        for i, future in enumerate(as_completed(futures)):
            res = future.result()
            if isinstance(res, list):
                results.extend(res)
            else:
                results.append(res)

            # Update progress bar
            progress_bar.progress((i + 1) / total_files)
            progress_text.text(f"Processing file {i+1}/{total_files}...")

    # Prepare DataFrame and persist results
    if results:
        df = pd.DataFrame(results)
        if "Extracted_ID" in df.columns:
            df["Status"] = df["Extracted_ID"].duplicated(keep=False).map(
                {True: "Duplicate", False: "Unique"}
            )
        st.session_state.results_df = df
    st.session_state.is_processing = False
    st.rerun()

# ----------------------------
# Results display and download (persisted)
# ----------------------------
if st.session_state.results_df is not None:
    df = st.session_state.results_df
    st.success(f"✅ Processed {len(df)} files successfully!")
    st.dataframe(df, use_container_width=True)

    errors = df[df["Error"].notna()]
    if not errors.empty:
        st.error("⚠️ Some files could not be processed:")
        st.table(errors[["File", "Error"]])

    output_file = "extracted_ids.xlsx"
    df.to_excel(output_file, index=False)
    with open(output_file, "rb") as f:
        st.download_button(
            label="⬇️ Download Excel",
            data=f,
            file_name=output_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
