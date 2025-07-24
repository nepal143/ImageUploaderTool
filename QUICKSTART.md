# Streamlined Image Processor - Quick Start

## 🚀 One Command Setup & Run

```bash
python streamlined_processor.py
```

## What This Does

This tool automatically:
1. **Cleans up** all old processed images and logs
2. **Downloads** images from your MySQL database 
3. **Finds** old logos (logo.webp) in the images
4. **Replaces** them with new logos (1753103783318.jpeg)
5. **Saves** processed images organized by report

## Required Files

✅ `logo.webp` - Your old logo (to be replaced)  
✅ `1753103783318.jpeg` - Your new logo (replacement)  
✅ `.env` - Database configuration  

## Database Configuration

Your `.env` file should contain:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=root  
DB_NAME=marketresearch
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET_NAME=
S3_FOLDER_PREFIX=processed-images/
```

## Expected Database Structure

```sql
table: report_sections
- id (int, primary key)
- report_id (int)
- heading (varchar)
- content (json) -- Contains objects with type:"image" and src/url
```

## Output

Processed images saved to:
```
processed_images/by_report/report_X/
```

With filenames like: `report_1519_section_256_img_0.png`

## Options

- **All reports**: Press Enter when prompted
- **Specific report**: Enter report ID (e.g., 1519)

## Features

🧹 **Auto cleanup** - Removes old data before each run  
🔍 **Smart detection** - Finds logos using template matching + corner detection  
🔄 **Logo replacement** - Automatically replaces old logos with new ones  
📁 **Organized output** - Files sorted by report ID  
📊 **Detailed reporting** - Shows download and replacement statistics

## Troubleshooting

- **No logos found**: Check that logo.webp matches logos in your images
- **No images downloaded**: Verify database connection and report_sections table
- **Permission errors**: Ensure write access to current directory
