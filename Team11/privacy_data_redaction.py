import boto3
import pandas as pd
from bs4 import BeautifulSoup
import docx
import chardet


def read_text_from_offsets(input_text, begin_offset, end_offset):
    if begin_offset < 0 or end_offset > len(input_text) or begin_offset > end_offset:
        raise ValueError("Invalid offset values")

    return input_text[begin_offset:end_offset+1]


def redact_number(number_entity, document):
    begin_offset = number_entity['BeginOffset']
    end_offset = number_entity['EndOffset']
    number_text = read_text_from_offsets(document, begin_offset, end_offset-1)
    replacement_text = ''.join('X' if char.isdigit() else char for char in number_text)
    # Replace the phone number with XXX-XXX-XXXX
    return document[:begin_offset] + replacement_text + document[end_offset:]


def detect_pii(document_text):
    client = boto3.client('comprehend')

    response = client.detect_pii_entities(
        Text=document_text,
        LanguageCode='en'
    )

    print(response)
    for entity in response['Entities']:
        if entity['Type'] == 'PHONE' or entity['Type'] == 'SSN' or entity['Type'] == 'DATE_TIME' or entity['Type'] == 'BANK_ACCOUNT_NUMBER':
            document_text = redact_number(entity, document_text)

    return document_text


s3 = boto3.client('s3')


def load_and_read_s3_files(bucket_name, prefix):
    """
    Loads multiple files from S3 bucket and reads their content.

    Args:
        bucket_name: The name of the S3 bucket.
        prefix: The prefix to filter files.

    Returns:
        A list of file contents.
    """

    s3 = boto3.client('s3')

    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    file_data = []
    for obj in response['Contents']:
        file_key = obj['Key']

        if (file_key != prefix):
            # Download the file to a temporary location
            temp_file_path = 'temp.docx'
            s3.download_file(bucket_name, file_key, temp_file_path)

            # Extract text from the downloaded file
            doc = docx.Document(temp_file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)

            file_data.append((file_key, '\n'.join(full_text)))

    return file_data


bucket_name = 'team21document'
prefix = "input_documents/"  # Optional, to filter files

file_contents = load_and_read_s3_files(bucket_name, prefix)

for filename, content in file_contents:
    print(f"Filename: {filename}")
    print(f"Content:")
    print("------------------------------------------------------------------")
    print(content)
    print("------------------------------------------------------------------")
    print("Entities Identified through Comprehend model :")
    redacted_text = detect_pii(content)
    print("------------------------------------------------------------------")
    print("Redacted_Content :")
    print(redacted_text)
