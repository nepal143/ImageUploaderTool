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
5. **Uploads** processed images to AWS S3
6. **Updates** database URLs to point to new S3 locations
7. **Saves** processed images organized by report

## Required Files

✅ `logo.webp` - Your old logo (to be replaced)  
✅ `1753103783318.jpeg` - Your new logo (replacement)  
✅ `.env` - Database configuration  

## Database Configuration

Your `.env` file should contain:
```env
# Database Settings
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=root  
DB_NAME=marketresearch

# AWS S3 Settings
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_FOLDER_PREFIX=processed-images/
```

**Note**: S3 configuration is optional. If not provided, images will only be processed locally.

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

If S3 is configured, images are also uploaded to:
```
s3://your-bucket/processed-images/by_report/report_X/
```

And database URLs are updated from:
```
"src": "https://old-source.com/image.png"
```
To:
```
"src": "https://your-bucket.s3.region.amazonaws.com/processed-images/..."
```

## Running Options

The script processes **ALL reports** in your database by default.

To process a specific report, modify the `main()` function:
```python
# For specific report
results = processor.process_all(report_id=1519)
```

## Features

🧹 **Auto cleanup** - Removes old data before each run  
🔍 **Smart detection** - Finds logos using template matching + corner detection  
🔄 **Logo replacement** - Automatically replaces old logos with new ones  
☁️ **S3 upload** - Uploads processed images to AWS S3  
�️ **Database update** - Updates image URLs in database to point to S3  
�📁 **Organized output** - Files sorted by report ID  
📊 **Detailed reporting** - Shows download, replacement, and upload statistics

## Alternative Scripts

- `test_s3_access.py` - Test your S3 permissions
- `test_core_workflow.py` - Test everything except S3
- `test_db_url_replacement.py` - Test database URL updates

## Troubleshooting

### Common Issues:

**No logos found**: 
- Check that `logo.webp` matches logos in your images
- Logo detection uses template matching - logos need reasonable similarity

**No images downloaded**: 
- Verify database connection settings in `.env`
- Check that `report_sections` table exists with proper structure

**S3 upload fails**: 
- Verify AWS credentials in `.env`
- Check S3 permissions (need `s3:PutObject` permission)
- Remove any AWS permissions boundary that blocks S3 actions

**Database URLs not updated**:
- This only happens after successful S3 upload
- Fix S3 issues first, then database will update automatically

**Permission errors**: 
- Ensure write access to current directory
- Run from the project root directory
