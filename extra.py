import streamlit as st
import zipfile
import io
import os
import re
import pandas as pd
from PyPDF2 import PdfReader

# ----------------------------
# Streamlit config
# ----------------------------
st.set_page_config(page_title="PDF ID Extractor", layout="wide")
st.title("📂 PDF ID Extractor (PDFs & ZIP Files)")

# Increase max upload size to 200 MB
st.set_option('server.maxUploadSize', 200)

# File uploader - multiple PDFs or ZIPs
uploaded_files = st.file_uploader(
    "Upload PDFs or ZIP files (multiple allowed)",
    type=["pdf", "zip"],
    accept_multiple_files=True
)

# Data storage
data = []

# Process uploaded files
if uploaded_files:
    with st.spinner("⏳ Processing files..."):
        for file in uploaded_files:
            filename = file.name
            try:
                # ----------------------------
                # Process single PDF
                # ----------------------------
                if filename.lower().endswith(".pdf"):
                    reader = PdfReader(file)
                    text = "".join([page.extract_text() or "" for page in reader.pages])

                    match = re.search(r"\b\d{18,22}\b", text)
                    extracted_id = match.group(0) if match else None

                    data.append({
                        "File": filename,
                        "Extracted_ID": extracted_id
                    })

                # ----------------------------
                # Process ZIP file
                # ----------------------------
                elif filename.lower().endswith(".zip"):
                    with zipfile.ZipFile(file) as z:
                        for file_info in z.infolist():
                            if file_info.filename.lower().endswith(".pdf"):
                                with z.open(file_info) as pdf_file:
                                    reader = PdfReader(pdf_file)
                                    text = "".join([page.extract_text() or "" for page in reader.pages])

                                    match = re.search(r"\b\d{18,22}\b", text)
                                    extracted_id = match.group(0) if match else None

                                    data.append({
                                        "File": file_info.filename,
                                        "Extracted_ID": extracted_id
                                    })
            except Exception as e:
                st.warning(f"⚠️ Could not process {filename}: {e}")

    # ----------------------------
    # Display results
    # ----------------------------
    if data:
        df = pd.DataFrame(data)
        df["Status"] = df["Extracted_ID"].duplicated(keep=False).map(
            {True: "Duplicate", False: "Unique"}
        )

        st.success(f"✅ Processed {len(data)} files successfully!")
        st.dataframe(df, use_container_width=True)

        # Save to Excel
        output_file = "extracted_ids.xlsx"
        df.to_excel(output_file, index=False)

        # Download button
        with open(output_file, "rb") as f:
            st.download_button(
                label="⬇️ Download Excel",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
