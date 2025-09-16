import streamlit as st
import zipfile
import io
import os
import re
import pandas as pd
from PyPDF2 import PdfReader

st.title("📂 PDF ID Extractor (Folder or ZIP Upload)")

# Choice: Folder path (local) or ZIP upload
choice = st.radio("Select input type:", ("Upload ZIP file", "Local folder"))

data = []

if choice == "Upload ZIP file":
    uploaded_zip = st.file_uploader("Upload a ZIP file containing PDFs", type=["zip"])
    
    if uploaded_zip:
        with zipfile.ZipFile(uploaded_zip) as z:
            for file_info in z.infolist():
                if file_info.filename.lower().endswith(".pdf"):
                    with z.open(file_info) as pdf_file:
                        reader = PdfReader(pdf_file)
                        text = ""
                        for page in reader.pages:
                            if page.extract_text():
                                text += page.extract_text() + "\n"

                        match = re.search(r"\b\d{18,22}\b", text)
                        extracted_id = match.group(0) if match else None

                        data.append({
                            "File": file_info.filename,
                            "Extracted_ID": extracted_id
                        })

elif choice == "Local folder":
    folder_path = st.text_input("Enter local folder path containing PDFs:")
    
    if folder_path and os.path.exists(folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file_name in files:
                if file_name.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, file_name)
                    reader = PdfReader(pdf_path)
                    text = ""
                    for page in reader.pages:
                        if page.extract_text():
                            text += page.extract_text() + "\n"

                    match = re.search(r"\b\d{18,22}\b", text)
                    extracted_id = match.group(0) if match else None

                    # Relative path for clarity
                    relative_path = os.path.relpath(pdf_path, folder_path)
                    data.append({
                        "File": relative_path,
                        "Extracted_ID": extracted_id
                    })

# If data collected, show results
if data:
    df = pd.DataFrame(data)
    df["Status"] = df["Extracted_ID"].duplicated(keep=False).map(
        {True: "Duplicate", False: "Unique"}
    )

    st.dataframe(df)

    # Save results to Excel
    output_file = "extracted_ids.xlsx"
    df.to_excel(output_file, index=False)

    # Download button
    with open(output_file, "rb") as f:
        st.download_button(
            label="⬇️ Download Excel",
            data=f,
            file_name="extracted_ids.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
