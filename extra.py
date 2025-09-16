import streamlit as st
import re
import pandas as pd
from PyPDF2 import PdfReader

st.title("📂 PDF ID Extractor")

# File uploader - allow multiple PDFs
uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    data = []

    for file in uploaded_files:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"

        # Extract long numeric ID (18–22 digits)
        match = re.search(r"\b\d{18,22}\b", text)
        extracted_id = match.group(0) if match else None

        data.append({"File": file.name, "Extracted_ID": extracted_id})

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Mark Duplicate / Unique
    df["Status"] = df["Extracted_ID"].duplicated(keep=False).map(
        {True: "Duplicate", False: "Unique"}
    )

    # Show results in app
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
