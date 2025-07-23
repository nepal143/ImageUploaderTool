# Streamlined Image Processor with Logo Replacement

A Python tool that downloads images from MySQL database and automatically replaces old logos with new ones.

## Features

- **Automatic Cleanup**: Removes old data before each run
- **Database Integration**: Downloads images from report_sections table
- **Logo Detection**: Finds old logos using template matching and corner detection
- **Logo Replacement**: Replaces old logos (logo.webp) with new ones (1753103783318.jpeg)
- **Smart Detection**: Uses both template matching and corner-based detection
- **Organized Output**: Saves processed images in organized folder structure

## Files

- `streamlined_processor.py` - Main processing tool
- `image_downloader.py` - Original downloader (legacy)
- `logo.webp` - Old logo to be replaced
- `1753103783318.jpeg` - New logo for replacement
- `.env` - Database configuration

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure database** in `.env`:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=root
DB_NAME=marketresearch
```

3. **Run the processor**:
```bash
python streamlined_processor.py
```

## What It Does

1. **Cleans up** all old processed images and logs
2. **Connects** to your MySQL database
3. **Fetches** report sections with JSON content
4. **Downloads** images from URLs in the content
5. **Detects** old logos (logo.webp) in downloaded images
6. **Replaces** old logos with new ones (1753103783318.jpeg)
7. **Organizes** processed images by report ID

## Output Structure

```
processed_images/
└── by_report/
    ├── report_1519/
    │   ├── report_1519_section_256_img_0.png (with new logo)
    │   └── report_1519_section_258_img_0.png (with new logo)
    └── report_1520/
        └── report_1520_section_301_img_0.jpg (with new logo)
```

## Database Structure Expected

```sql
table: report_sections
- id (int, primary key)
- report_id (int)
- heading (varchar)
- content (json) -- Array of objects with type: "image" and src/url fields
```

## JSON Content Format

```json
[
  {
    "type": "image", 
    "src": "https://example.com/image.jpg",
    "alt": "Description"
  }
]
```

## Logo Detection

The tool uses two methods to find old logos:

1. **Template Matching**: OpenCV-based detection for exact matches
2. **Corner Detection**: Checks common logo positions (bottom-left, bottom-right, etc.)

## Configuration

- **Database**: Configure in `.env` file
- **Logo files**: Place `logo.webp` (old) and `1753103783318.jpeg` (new) in root directory
- **Detection threshold**: Adjustable in code (default: 0.7)

## Features

✅ **Automatic cleanup** of old data  
✅ **Database integration** with MySQL  
✅ **Smart logo detection** using multiple methods  
✅ **High-quality image processing** with PIL and OpenCV  
✅ **Organized file structure** by report  
✅ **Comprehensive logging** and error handling  
✅ **Batch processing** of all reports or specific report ID
