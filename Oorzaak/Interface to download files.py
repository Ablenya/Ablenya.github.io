# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 10:44:28 2025

@author: ABarros
"""

from flask import Flask, render_template, request, send_file
import io
import zipfile
import pandas as pd
import numpy as np
from io import BytesIO

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# -------------------------------------------------------------------------
# Google Drive API Setup
# -------------------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'peak-study-411014-e9e4cb207ff0.json'  # Update this path

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# -------------------------------------------------------------------------
# ID of the parent folder in Google Drive that contains your period folders
# (e.g., Antwerp period 1, etc.)
# -------------------------------------------------------------------------
PARENT_FOLDER_ID = '1YF0jFom6oc5E_Tfw6wc5DXEYYN4khx1V'  # Update this ID

# -------------------------------------------------------------------------
# Global In-Memory Caches
# -------------------------------------------------------------------------
# We store the raw file bytes (for "original" download) and the lastModified time
MODIFIED_CACHE_BYTES = {}  # { file_id: last_modified_time }
FILE_BYTES_CACHE = {}       # { file_id: bytes }

# We store the parsed workbook (dict of sheet_name->DataFrame) and lastModified time
MODIFIED_CACHE_WORKBOOK = {}  # { file_id: last_modified_time }
WORKBOOK_CACHE = {}           # { file_id: { "Sheet1": df, ... } }

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def list_folders(parent_id):
    """List subfolders under a given parent folder in Google Drive."""
    query = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def list_files(folder_id):
    all_files = []
    page_token = None
    
    while True:
        query = (f"'{folder_id}' in parents and "
                 f"mimeType != 'application/vnd.google-apps.folder' and trashed = false")
        response = drive_service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, size, modifiedTime)",
            pageSize=100,     # or up to 1000
            pageToken=page_token
        ).execute()
        
        files = response.get('files', [])
        all_files.extend(files)
        
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    
    return all_files

def download_file_raw(file_id):
    """
    Actually download a file from Google Drive and return its raw bytes.
    (Used internally by get_file_bytes if caching is invalid or stale.)
    """
    request_drive = drive_service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request_drive)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    file_stream.seek(0)
    return file_stream.read()

def get_file_bytes(file_id):
    """
    Returns the raw bytes for the specified file.
    Uses caching based on last modified time to skip re-download if unchanged.
    """
    # 1) Check file's modified time
    info = drive_service.files().get(fileId=file_id, fields="modifiedTime, name").execute()
    mod_time = info["modifiedTime"]
    
    # 2) Compare with our cache
    if file_id in MODIFIED_CACHE_BYTES and MODIFIED_CACHE_BYTES[file_id] == mod_time:
        # It's cached and hasn't changed
        return FILE_BYTES_CACHE[file_id]
    
    # 3) If not cached or it's changed, re-download
    raw_data = download_file_raw(file_id)
    FILE_BYTES_CACHE[file_id] = raw_data
    MODIFIED_CACHE_BYTES[file_id] = mod_time
    return raw_data

def get_workbook(file_id):
    """
    Returns a dict of { sheet_name: DataFrame } for the file.
    Caches the parsed workbook by last modified time to skip re-parsing.
    """
    # 1) Check file's modified time
    info = drive_service.files().get(fileId=file_id, fields="modifiedTime, name").execute()
    mod_time = info["modifiedTime"]
    
    # 2) Compare with our cache
    if file_id in MODIFIED_CACHE_WORKBOOK and MODIFIED_CACHE_WORKBOOK[file_id] == mod_time:
        # It's cached and hasn't changed
        return WORKBOOK_CACHE[file_id]
    
    # 3) If not cached or changed, re-download & parse all sheets at once
    raw_data = get_file_bytes(file_id)  # uses the function above for raw bytes
    workbook = pd.read_excel(BytesIO(raw_data), sheet_name=None)
    
    # 4) Store in cache
    WORKBOOK_CACHE[file_id] = workbook
    MODIFIED_CACHE_WORKBOOK[file_id] = mod_time
    return workbook

# -------------------------------------------------------------------------
# Flask Routes
# -------------------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    folders = list_folders(PARENT_FOLDER_ID)
    
    if request.method == 'POST':
        selected_folder_id = request.form.get('folder')
        selected_files_ids = request.form.getlist('files')
        download_options = request.form.getlist('options')
        
        # Return early if no option chosen (uncomment if needed)
        # if not download_options:
        #     return "No download option selected.", 400
        
        memory_zip = BytesIO()
        with zipfile.ZipFile(memory_zip, 'w') as zf:
            # -----------------------------------------------------------
            # Option 1: Download Original Files
            # -----------------------------------------------------------
            if 'original' in download_options:
                for file_id in selected_files_ids:
                    info = drive_service.files().get(fileId=file_id, fields="name").execute()
                    file_name = info['name']
                    file_data = get_file_bytes(file_id)  # <-- get raw bytes from cache or fresh download
                    zf.writestr(f"Individual reports/{file_name}", file_data)
            
            # -----------------------------------------------------------
            # Option 2: Download Compiled Files
            # -----------------------------------------------------------
            if 'compiled' in download_options:
                sheets_to_compile = [
                    'Measurement averages',
                    'Weekly averages',
                    'Parameters daily',
                    'Parameters hourly'
                ]
                compiled_sheets = {sheet: [] for sheet in sheets_to_compile}
                
                for file_id in selected_files_ids:
                    workbook = get_workbook(file_id)  # parse once, get all sheets
                    for sheet in sheets_to_compile:
                        df = workbook.get(sheet)
                        if df is not None:
                            compiled_sheets[sheet].append(df)

                # Grab folder name for file naming
                folder_info = drive_service.files().get(fileId=selected_folder_id, fields="name").execute()
                folder_name = folder_info.get("name")
                
                for sheet, df_list in compiled_sheets.items():
                    if df_list:
                        compiled_df = pd.concat(df_list, ignore_index=True)
                        excel_io = BytesIO()
                        compiled_df.to_excel(excel_io, index=False)
                        excel_io.seek(0)
                        file_name = f"{sheet} {folder_name}.xlsx"
                        zf.writestr(f"Compiled files/{file_name}", excel_io.read())
            
            # -----------------------------------------------------------
            # Option 3: Download Overview
            # -----------------------------------------------------------
            if 'overview' in download_options:
                metadata_list = []
                measurement_avg_list = []
                weekly_avg_list = []
                daily_avg_list = []
                hourly_avg_list = []
                
                # 1) Gather data from all selected files
                for file_id in selected_files_ids:
                    workbook = get_workbook(file_id)  # parse once, get all sheets
                    # Metadata
                    df_meta = workbook.get("Metadata")
                    if df_meta is not None and "ID" in df_meta.columns:
                        metadata_list.append(df_meta[["ID"]])
                    
                    # Measurement
                    df_meas = workbook.get("Measurement averages")
                    if df_meas is not None:
                        measurement_avg_list.append(df_meas)
                    
                    # Weekly
                    df_week = workbook.get("Weekly averages")
                    if df_week is not None:
                        weekly_avg_list.append(df_week)
                    
                    # Daily
                    df_daily = workbook.get("Parameters daily")
                    if df_daily is not None:
                        daily_avg_list.append(df_daily)
                    
                    # Hourly
                    df_hourly = workbook.get("Parameters hourly")
                    if df_hourly is not None:
                        hourly_avg_list.append(df_hourly)
                
                # 2) Create Overviews
                # ------------------- (A) Metadata 
                if metadata_list:
                    metadata_overview = pd.concat(metadata_list, ignore_index=True).drop_duplicates()
                else:
                    metadata_overview = pd.DataFrame(columns=["ID"])
                
                # ------------------- (B) Measurement Averages
                if measurement_avg_list:
                    ref = measurement_avg_list[0]
                    try:
                        start_idx = ref.columns.get_loc("lden")
                        end_idx = ref.columns.get_loc("lceq_1min_moving_average")
                        numeric_cols = ref.columns[start_idx:end_idx+1]
                        
                        period_col = ref["Period"]
                        # sum+count for ignoring NaNs
                        sum_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        count_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        
                        for df in measurement_avg_list:
                            data = df[numeric_cols].copy()
                            valid_mask = data.notna()
                            data_filled = data.fillna(0)
                            sum_df += data_filled
                            count_df += valid_mask.astype(float)
                        
                        count_df.replace(0, np.nan, inplace=True)
                        avg_df = sum_df / count_df
                        avg_df=avg_df.round(1)
                        measurement_overview = pd.concat([period_col, avg_df], axis=1)
                    except Exception as e:
                        print("Error processing Measurement averages overview:", e)
                        measurement_overview = pd.DataFrame()
                else:
                    measurement_overview = pd.DataFrame()
                
                # ------------------- (C) Weekly Averages
                if weekly_avg_list:
                    ref = weekly_avg_list[0]
                    try:
                        start_idx = ref.columns.get_loc("lden")
                        end_idx = ref.columns.get_loc("lceq_1min_moving_average")
                        numeric_cols = ref.columns[start_idx:end_idx+1]
                        fixed_cols = ref[["Week_survey","Period"]]
                        sum_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        count_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        
                        for df in weekly_avg_list:
                            data = df[numeric_cols].copy()
                            valid_mask = data.notna()
                            data_filled = data.fillna(0)
                            sum_df += data_filled
                            count_df += valid_mask.astype(float)
                        
                        count_df.replace(0, np.nan, inplace=True)
                        avg_df = sum_df / count_df
                        avg_df=avg_df.round(1)
                        weekly_overview = pd.concat([fixed_cols, avg_df], axis=1)
                    except Exception as e:
                        print("Error processing weekly averages overview:", e)
                        weekly_overview = pd.DataFrame()
                else:
                    weekly_overview = pd.DataFrame()
                
                # ------------------- (D) Daily Averages
                if daily_avg_list:
                    ref = daily_avg_list[0]
                    try:
                        start_idx = ref.columns.get_loc("laeq")
                        end_idx = ref.columns.get_loc("lceq_1min_moving_average")
                        numeric_cols = ref.columns[start_idx:end_idx+1]
                        
                        fixed_data = ref[[
                            "Date", "Day", "Weekday", "Holiday", 
                            "Workday", "Week", "Week_survey", "Valid"
                        ]]
                        
                        sum_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        count_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        
                        for df in daily_avg_list:
                            data = df[numeric_cols].copy()
                            valid_mask = data.notna()
                            data_filled = data.fillna(0)
                            sum_df += data_filled
                            count_df += valid_mask.astype(float)
                        
                        count_df.replace(0, np.nan, inplace=True)
                        avg_df = sum_df / count_df
                        avg_df=avg_df.round(1)
                        daily_overview = pd.concat([fixed_data, avg_df], axis=1)
                    except Exception as e:
                        print("Error processing daily averages overview:", e)
                        daily_overview = pd.DataFrame()
                else:
                    daily_overview = pd.DataFrame()
                
                # ------------------- (E) Hourly Averages
                if hourly_avg_list:
                    ref = hourly_avg_list[0]
                    try:
                        start_idx = ref.columns.get_loc("laeq")
                        end_idx = ref.columns.get_loc("lceq_1min_moving_average")
                        numeric_cols = ref.columns[start_idx:end_idx+1]
                        
                        fixed_data = ref[[
                            "Date", "Time", "Hour", "Day", "Weekday", "Holiday", 
                            "Workday", "Week", "Week_survey", "Period", "Valid"
                        ]]
                        
                        sum_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        count_df = pd.DataFrame(0, index=ref.index, columns=numeric_cols, dtype=float)
                        
                        for df in hourly_avg_list:
                            data = df[numeric_cols].copy()
                            valid_mask = data.notna()
                            data_filled = data.fillna(0)
                            sum_df += data_filled
                            count_df += valid_mask.astype(float)
                        
                        count_df.replace(0, np.nan, inplace=True)
                        avg_df = sum_df / count_df
                        avg_df=avg_df.round(1)
                        hourly_overview = pd.concat([fixed_data, avg_df], axis=1)
                    except Exception as e:
                        print("Error processing hourly averages overview:", e)
                        hourly_overview = pd.DataFrame()
                else:
                    hourly_overview = pd.DataFrame()
                
                # 3) Write the overview data to an Excel file
                overview_io = BytesIO()
                with pd.ExcelWriter(overview_io, engine='openpyxl') as writer:
                    metadata_overview.to_excel(writer, sheet_name="Measurement points", index=False)
                    measurement_overview.to_excel(writer, sheet_name="Measurement averages", index=False)
                    weekly_overview.to_excel(writer, sheet_name="Weekly averages", index=False)
                    daily_overview.to_excel(writer, sheet_name="Daily averages", index=False)
                    hourly_overview.to_excel(writer, sheet_name="Hourly averages", index=False)
                
                overview_io.seek(0)
                zf.writestr("Overview/Overview reports.xlsx", overview_io.read())
        
        memory_zip.seek(0)
        return send_file(memory_zip, download_name='downloaded_files.zip', as_attachment=True)
    
    # GET request
    return render_template('index.html', folders=folders)

@app.route('/files/<folder_id>')
def files(folder_id):
    files_list = list_files(folder_id)
    return render_template('files.html', files=files_list)

if __name__ == '__main__':
    # app.run(debug=True)
    app.run()