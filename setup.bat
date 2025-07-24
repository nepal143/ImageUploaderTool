@echo off
echo Image Downloader Tool Setup
echo ==========================

echo Installing required packages...
"B:/market research/ImageUploaderTool/.venv/Scripts/pip.exe" install -r requirements.txt

echo.
echo Testing installation...
"B:/market research/ImageUploaderTool/.venv/Scripts/python.exe" -c "import mysql.connector; import requests; import PIL; print('All packages imported successfully!')"

echo.
echo Setup complete!
echo.
echo To run the image downloader:
echo "B:/market research/ImageUploaderTool/.venv/Scripts/python.exe" image_downloader.py
echo.
echo To run the example:
echo "B:/market research/ImageUploaderTool/.venv/Scripts/python.exe" example.py

pause
