# Streamlined Image Processor - Technical Documentation

## 📖 Overview

The **Streamlined Image Processor** automates logo replacement in marketing research reports. It downloads images from MySQL, replaces old logos with new ones, uploads to AWS S3, and updates database URLs.

**Key Features:**
- Automated end-to-end processing
- Smart logo detection and replacement
- AWS S3 integration with database updates
- Organized file structure

## 🏗️ Workflow

```
MySQL Database → Download Images → Logo Detection → Logo Replacement → S3 Upload → Database Update
```

**Process:**
1. Query database for report sections containing images
2. Download images locally
3. Detect and replace old logos using OpenCV
4. Upload processed images to S3
5. Update database with new S3 URLs

## 🔧 Core Components

**Main Class: `StreamlinedImageProcessor`**

Key methods:
- `fetch_report_sections()` - Gets data from MySQL
- `download_image()` - Downloads images with verification
- `find_and_replace_logo()` - Logo detection and replacement
- `upload_processed_images_to_s3()` - S3 upload + DB update
- `update_image_url_in_db()` - Updates URLs in database

## � Database Schema

```sql
CREATE TABLE report_sections (
    id INT PRIMARY KEY,
    report_id INT,
    content JSON  -- Contains image objects with URLs
);
```

**JSON Structure:**
```json
[{
    "type": "image",
    "src": "https://example.com/image.png",
    "alt": "Description"
}]
```

## ☁️ S3 Configuration

**Required Environment Variables:**
```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket
S3_FOLDER_PREFIX=processed-images/
```

**Required S3 Permissions:**
- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket`

## 🖼️ Logo Processing

**Detection Methods:**
1. **Template Matching** - OpenCV pattern matching at multiple scales
2. **Corner Detection** - Fallback for common logo positions

**Replacement Process:**
1. Sample surrounding colors for background
2. Fill old logo area with background color
3. Find optimal position for new logo (avoids text/busy areas)
4. Place new logo with proper scaling

## ⚙️ Configuration

**Required Files:**
- `.env` - Database and AWS credentials
- `logo.webp` - Old logo to detect
- `1753103783318.jpeg` - New logo replacement
- `requirements.txt` - Python dependencies

**Database Config:**
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=marketresearch
```

## 🚀 Usage

**Basic Usage:**
```python
processor = StreamlinedImageProcessor()
results = processor.process_all()  # Process all reports
results = processor.process_all(report_id=1519)  # Specific report
```

## 📊 Output Structure

```
processed_images/
└── by_report/
    └── report_1519/
        ├── report_1519_section_256_img_0.png
        └── report_1519_section_258_img_0.png

S3: s3://bucket/processed-images/by_report/report_1519/...
```

**Return Data:**
```python
{
    'total_sections': 11,
    'sections_with_images': 3,
    'successful_downloads': 3,
    'logo_replacements': 1,
    's3_upload': {'uploaded': 3, 'failed': 0}
}
```

## 🔧 Testing & Troubleshooting

**Test Scripts:**
- `test_s3_access.py` - Verify S3 permissions
- `test_core_workflow.py` - Test local processing
- `test_db_url_replacement.py` - Test database updates

**Common Issues:**
1. **S3 Permissions** - Check IAM policies
2. **Database Connection** - Verify `.env` credentials  
3. **Logo Detection** - Adjust threshold in `find_and_replace_logo()`
4. **Missing Files** - Ensure `logo.webp` and `1753103783318.jpeg` exist

**Dependencies:**
```bash
pip install mysql-connector-python requests Pillow opencv-python boto3 python-dotenv numpy
```

---

This tool provides automated logo replacement with cloud integration for marketing research reports.
