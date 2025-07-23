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
echo To run the streamlined processor:
echo "B:/market research/ImageUploaderTool/.venv/Scripts/python.exe" streamlined_processor.py
echo.
echo To test S3 access:
echo "B:/market research/ImageUploaderTool/.venv/Scripts/python.exe" test_s3_access.py
echo.
echo To test core workflow:
echo "B:/market research/ImageUploaderTool/.venv/Scripts/python.exe" test_core_workflow.py

pause
