#!/usr/bin/env python3
"""
Streamlined Image Processor with Logo Replacement

This tool downloads images from the database and replaces old logos with new ones.
It cleans up old data before each run.
"""

import os
import shutil
import logging
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import mysql.connector
import requests
import json
from PIL import Image
import cv2
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StreamlinedImageProcessor:
    """Downloads images and replaces logos in one streamlined process."""
    
    def __init__(self):
        """Initialize the processor."""
        # Database configuration
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'root'),
            'database': os.getenv('DB_NAME', 'marketresearch'),
            'charset': 'utf8mb4'
        }
        
        # S3 configuration
        self.s3_config = {
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'region_name': os.getenv('AWS_REGION', 'us-east-1'),
            'bucket_name': os.getenv('S3_BUCKET_NAME'),
            'folder_prefix': os.getenv('S3_FOLDER_PREFIX', 'processed-images/')
        }
        
        # Initialize S3 client if credentials are provided
        self.s3_client = None
        if (self.s3_config['aws_access_key_id'] and 
            self.s3_config['aws_secret_access_key'] and 
            self.s3_config['bucket_name'] and
            self.s3_config['aws_access_key_id'].strip() and
            self.s3_config['aws_secret_access_key'].strip() and
            self.s3_config['bucket_name'].strip()):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.s3_config['aws_access_key_id'],
                    aws_secret_access_key=self.s3_config['aws_secret_access_key'],
                    region_name=self.s3_config['region_name']
                )
                # Test the connection by listing buckets (but don't fail if it doesn't work)
                try:
                    self.s3_client.head_bucket(Bucket=self.s3_config['bucket_name'])
                    logger.info(f"✅ S3 client initialized and bucket verified: {self.s3_config['bucket_name']}")
                except Exception as e:
                    logger.warning(f"⚠️ S3 bucket verification failed: {e}")
                    logger.info("S3 uploads will be attempted but may fail")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
        else:
            logger.info("ℹ️ S3 credentials not provided - S3 upload will be skipped")
        
        # Paths
        self.download_dir = Path('processed_images')
        self.old_logo_path = Path('logo.webp')
        self.new_logo_path = Path('1753103783318.jpeg')
        
        # Verify logo files exist
        if not self.old_logo_path.exists():
            raise FileNotFoundError(f"Old logo not found: {self.old_logo_path}")
        if not self.new_logo_path.exists():
            raise FileNotFoundError(f"New logo not found: {self.new_logo_path}")
        
        # Load logos
        self.old_logo = Image.open(self.old_logo_path).convert('RGBA')
        self.new_logo = Image.open(self.new_logo_path).convert('RGBA')
        
        logger.info(f"Old logo loaded: {self.old_logo_path} (Size: {self.old_logo.size})")
        logger.info(f"New logo loaded: {self.new_logo_path} (Size: {self.new_logo.size})")
    
    def cleanup_old_data(self):
        """Remove all old processed images and logs."""
        logger.info("Cleaning up old data...")
        
        # Remove processed images directory
        if self.download_dir.exists():
            shutil.rmtree(self.download_dir)
            logger.info(f"Removed old directory: {self.download_dir}")
        
        # Remove old log files (skip if in use)
        log_files = ['download_results.json']
        for log_file in log_files:
            log_path = Path(log_file)
            if log_path.exists():
                try:
                    log_path.unlink()
                    logger.info(f"Removed old log: {log_file}")
                except Exception:
                    pass  # Skip if file is in use
        
        # Create fresh directories
        self.download_dir.mkdir(exist_ok=True)
        (self.download_dir / 'by_report').mkdir(exist_ok=True)
        
        logger.info("Cleanup completed")
    
    def connect_to_database(self):
        """Connect to MySQL database."""
        try:
            connection = mysql.connector.connect(**self.db_config)
            logger.info("Successfully connected to MySQL database")
            return connection
        except mysql.connector.Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise
    
    def update_image_url_in_db(self, section_id: int, old_url: str, new_url: str):
        """Update the image URL in the database for a given section and old URL."""
        connection = None
        cursor = None
        try:
            connection = self.connect_to_database()
            cursor = connection.cursor()
            
            # Update the JSON content in the 'content' field of the report_sections table
            # Replace old_url with new_url in the JSON string
            update_query = """
                UPDATE report_sections
                SET content = REPLACE(content, %s, %s)
                WHERE id = %s
            """
            cursor.execute(update_query, (old_url, new_url, section_id))
            affected_rows = cursor.rowcount
            connection.commit()
            
            if affected_rows > 0:
                logger.info(f"✅ Updated DB: section {section_id} | {old_url} -> {new_url}")
            else:
                logger.warning(f"⚠️ No rows updated for section {section_id} - URL might not exist: {old_url}")
                
        except Exception as e:
            logger.error(f"❌ Failed to update DB for section {section_id}: {e}")
            if connection:
                connection.rollback()
        finally:
            try:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()
            except Exception:
                pass
    
    def fetch_report_sections(self, report_id: Optional[int] = None):
        """Fetch report sections from database."""
        connection = None
        try:
            connection = self.connect_to_database()
            cursor = connection.cursor(dictionary=True)
            
            if report_id:
                query = "SELECT id, report_id, heading, content FROM report_sections WHERE report_id = %s"
                cursor.execute(query, (report_id,))
            else:
                query = "SELECT id, report_id, heading, content FROM report_sections"
                cursor.execute(query)
            
            sections = cursor.fetchall()
            logger.info(f"Fetched {len(sections)} report sections")
            return sections
            
        except mysql.connector.Error as e:
            logger.error(f"Error fetching report sections: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def extract_image_urls(self, content: str):
        """Extract image URLs from JSON content."""
        try:
            if not content:
                return []
                
            content_data = json.loads(content)
            
            if not isinstance(content_data, list):
                content_data = [content_data]
            
            image_objects = []
            for item in content_data:
                if isinstance(item, dict) and item.get('type') == 'image':
                    if 'url' in item:
                        image_objects.append(item)
                    elif 'src' in item:
                        item['url'] = item['src']
                        image_objects.append(item)
            
            return image_objects
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON content: {e}")
            return []
    
    def download_image(self, url: str, filename: str, subfolder: str = ''):
        """Download image from URL."""
        try:
            if subfolder:
                download_path = self.download_dir / subfolder
                download_path.mkdir(exist_ok=True)
            else:
                download_path = self.download_dir
            
            full_path = download_path / filename
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL does not point to an image: {url}")
                return False
            
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify the image
            with Image.open(full_path) as img:
                img.verify()
            
            logger.info(f"Downloaded: {full_path}")
            return str(full_path)
                
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return False
    
    def find_empty_space_for_logo(self, image: Image.Image, logo_size: tuple, avoid_regions: list = None):
        """Find an appropriate empty space to place the new logo."""
        img_width, img_height = image.size
        logo_width, logo_height = logo_size
        
        # Convert image to grayscale for analysis
        gray_image = image.convert('L')
        image_array = np.array(gray_image)
        
        # Define candidate positions (preference order)
        candidate_positions = [
            # Bottom corners (most common for logos)
            ('bottom-left', 20, img_height - logo_height - 20),
            ('bottom-right', img_width - logo_width - 20, img_height - logo_height - 20),
            # Top corners  
            ('top-left', 20, 20),
            ('top-right', img_width - logo_width - 20, 20),
            # Bottom center
            ('bottom-center', (img_width - logo_width) // 2, img_height - logo_height - 20),
            # Top center
            ('top-center', (img_width - logo_width) // 2, 20),
        ]
        
        # Regions to avoid (old logo positions)
        avoid_regions = avoid_regions or []
        
        best_position = None
        best_score = -1
        
        for position_name, x, y in candidate_positions:
            # Check if position is within image bounds
            if x < 0 or y < 0 or x + logo_width > img_width or y + logo_height > img_height:
                continue
            
            # Check if position overlaps with regions to avoid
            overlaps_avoid_region = False
            for avoid_x, avoid_y, avoid_w, avoid_h in avoid_regions:
                if not (x + logo_width <= avoid_x or 
                       x >= avoid_x + avoid_w or 
                       y + logo_height <= avoid_y or 
                       y >= avoid_y + avoid_h):
                    overlaps_avoid_region = True
                    break
            
            if overlaps_avoid_region:
                continue
            
            # Extract the region where logo would be placed
            region = image_array[y:y+logo_height, x:x+logo_width]
            
            # Calculate "emptiness" score (higher is better)
            # Look for areas with consistent color/brightness
            mean_intensity = np.mean(region)
            std_intensity = np.std(region)
            
            # Prefer areas that are:
            # 1. Not too dark (avoid black areas)
            # 2. Not too bright (avoid white text areas) 
            # 3. Have low variation (consistent background)
            intensity_score = 1.0 - abs(mean_intensity - 128) / 128  # Prefer mid-tones
            consistency_score = 1.0 - min(std_intensity / 50, 1.0)  # Prefer low variation
            
            # Bonus for bottom positions (traditional logo placement)
            position_bonus = 0.3 if 'bottom' in position_name else 0.0
            
            total_score = intensity_score * 0.4 + consistency_score * 0.4 + position_bonus
            
            logger.debug(f"Position {position_name} at ({x}, {y}): score {total_score:.3f}")
            
            if total_score > best_score:
                best_score = total_score
                best_position = (position_name, x, y)
        
        if best_position:
            position_name, x, y = best_position
            logger.info(f"Selected position: {position_name} at ({x}, {y}) with score {best_score:.3f}")
            return (x, y)
        
        # Fallback to bottom-left with margin
        fallback_x, fallback_y = 20, img_height - logo_height - 20
        logger.info(f"Using fallback position: bottom-left at ({fallback_x}, {fallback_y})")
        return (fallback_x, fallback_y)
    
    def remove_old_logo(self, image: Image.Image, logo_position: tuple):
        """Remove/clear the old logo from its position."""
        x, y, w, h = logo_position
        
        # Create a copy to work with
        result_image = image.copy()
        
        # Extract the old logo region
        logo_region = image.crop((x, y, x + w, y + h))
        
        # Try to fill with surrounding background color
        # Sample colors from around the logo area (expanding outward)
        margin = 10
        sample_regions = []
        
        # Sample from left, right, top, bottom of logo
        if x - margin >= 0:
            sample_regions.append((x - margin, y, margin, h))  # Left
        if x + w + margin <= image.width:
            sample_regions.append((x + w, y, margin, h))  # Right
        if y - margin >= 0:
            sample_regions.append((x, y - margin, w, margin))  # Top
        if y + h + margin <= image.height:
            sample_regions.append((x, y + h, w, margin))  # Bottom
        
        # Calculate average background color
        if sample_regions:
            all_pixels = []
            for sx, sy, sw, sh in sample_regions:
                sample = image.crop((sx, sy, sx + sw, sy + sh))
                sample_array = np.array(sample)
                all_pixels.extend(sample_array.reshape(-1, sample_array.shape[-1]))
            
            if all_pixels:
                avg_color = tuple(map(int, np.mean(all_pixels, axis=0)))
            else:
                avg_color = (255, 255, 255)  # White fallback
        else:
            avg_color = (255, 255, 255)  # White fallback
        
        # Fill the old logo area with background color
        from PIL import ImageDraw
        draw = ImageDraw.Draw(result_image)
        draw.rectangle([x, y, x + w, y + h], fill=avg_color)
        
        logger.info(f"Removed old logo from ({x}, {y}) and filled with color {avg_color}")
        return result_image

    def find_and_replace_logo(self, image_path: str, threshold: float = 0.5):
        """Find old logo in image and replace with new logo in appropriate location."""
        try:
            # Load the main image
            with Image.open(image_path) as main_image:
                main_image = main_image.convert('RGBA')
                
                # Convert to OpenCV format for template matching
                image_cv = cv2.cvtColor(np.array(main_image.convert('RGB')), cv2.COLOR_RGB2BGR)
                template_cv = cv2.cvtColor(np.array(self.old_logo.convert('RGB')), cv2.COLOR_RGB2BGR)
                
                best_match = None
                best_similarity = 0
                best_scale = 1.0
                
                # Try multiple scales since logo might be different size
                scales = [0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5]
                
                for scale in scales:
                    new_width = int(self.old_logo.width * scale)
                    new_height = int(self.old_logo.height * scale)
                    
                    if new_width > 10 and new_height > 10 and new_width < main_image.width and new_height < main_image.height:
                        # Scale the template
                        scaled_logo = self.old_logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        scaled_template_cv = cv2.cvtColor(np.array(scaled_logo.convert('RGB')), cv2.COLOR_RGB2BGR)
                        
                        # Perform template matching
                        result = cv2.matchTemplate(image_cv, scaled_template_cv, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(result)
                        
                        if max_val > best_similarity:
                            best_similarity = max_val
                            best_match = (max_loc[0], max_loc[1], new_width, new_height)
                            best_scale = scale
                
                logger.info(f"Best match: similarity {best_similarity:.3f} at scale {best_scale}")
                
                positions = []
                if best_similarity > threshold and best_match:
                    positions = [best_match]
                    logger.info(f"Template matching found logo with similarity {best_similarity:.3f}")
                
                # Only try corner detection if template matching found nothing good
                if not positions:
                    logo_position = self._find_logo_in_corners(main_image, strict_threshold=0.6)
                    if logo_position:
                        positions = [logo_position]
                        logger.info("Corner detection found logo")
                
                if not positions:
                    logger.info(f"No old logo found in: {image_path}")
                    return False
                
                # Process each found logo position
                result_image = main_image.copy()
                logo_replaced = False
                
                for old_x, old_y, old_w, old_h in positions:
                    # Step 1: Remove the old logo by filling with background
                    result_image = self.remove_old_logo(result_image, (old_x, old_y, old_w, old_h))
                    
                    # Step 2: Calculate new logo size while preserving aspect ratio
                    new_width, new_height = self.new_logo.size
                    new_aspect_ratio = new_width / new_height
                    
                    # Use a reasonable size for the new logo (not necessarily same as old logo)
                    target_width = min(200, main_image.width // 8)  # Max 200px or 1/8 of image width
                    target_height = int(target_width / new_aspect_ratio)
                    
                    # Step 3: Find appropriate empty space for new logo
                    # Avoid the old logo position
                    avoid_regions = [(old_x, old_y, old_w, old_h)]
                    new_x, new_y = self.find_empty_space_for_logo(result_image, (target_width, target_height), avoid_regions)
                    
                    # Step 4: Resize and place new logo
                    new_logo_resized = self.new_logo.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    
                    # Paste new logo at the selected position
                    result_image.paste(new_logo_resized, (new_x, new_y), new_logo_resized)
                    
                    logger.info(f"Removed old logo from ({old_x}, {old_y}) and placed new logo at ({new_x}, {new_y}) with size ({target_width}, {target_height})")
                    logo_replaced = True
                
                if logo_replaced:
                    # Convert back to original format if needed
                    original_format = Image.open(image_path).format
                    if main_image.mode != 'RGBA' and original_format != 'PNG':
                        result_image = result_image.convert('RGB')
                    
                    # Save the result
                    result_image.save(image_path, quality=95, optimize=True)
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error processing logo replacement in {image_path}: {e}")
            return False
                
    def find_empty_space_for_logo(self, image: Image.Image, logo_size: tuple, avoid_regions: list = None):
        """Find an appropriate empty space to place the new logo."""
        img_width, img_height = image.size
        logo_width, logo_height = logo_size
        
        # Convert image to grayscale for analysis
        gray_image = image.convert('L')
        image_array = np.array(gray_image)
        
        # Define candidate positions (preference order)
        candidate_positions = [
            # Bottom corners (most common for logos)
            ('bottom-left', 20, img_height - logo_height - 20),
            ('bottom-right', img_width - logo_width - 20, img_height - logo_height - 20),
            # Top corners  
            ('top-left', 20, 20),
            ('top-right', img_width - logo_width - 20, 20),
            # Bottom center
            ('bottom-center', (img_width - logo_width) // 2, img_height - logo_height - 20),
            # Top center
            ('top-center', (img_width - logo_width) // 2, 20),
        ]
        
        # Regions to avoid (old logo positions)
        avoid_regions = avoid_regions or []
        
        best_position = None
        best_score = -1
        
        for position_name, x, y in candidate_positions:
            # Check if position is within image bounds
            if x < 0 or y < 0 or x + logo_width > img_width or y + logo_height > img_height:
                continue
            
            # Check if position overlaps with regions to avoid
            overlaps_avoid_region = False
            for avoid_x, avoid_y, avoid_w, avoid_h in avoid_regions:
                if not (x + logo_width <= avoid_x or 
                       x >= avoid_x + avoid_w or 
                       y + logo_height <= avoid_y or 
                       y >= avoid_y + avoid_h):
                    overlaps_avoid_region = True
                    break
            
            if overlaps_avoid_region:
                continue
            
            # Extract the region where logo would be placed
            region = image_array[y:y+logo_height, x:x+logo_width]
            
            # Calculate "emptiness" score (higher is better)
            # Look for areas with consistent color/brightness
            mean_intensity = np.mean(region)
            std_intensity = np.std(region)
            
            # Prefer areas that are:
            # 1. Not too dark (avoid black areas)
            # 2. Not too bright (avoid white text areas) 
            # 3. Have low variation (consistent background)
            intensity_score = 1.0 - abs(mean_intensity - 128) / 128  # Prefer mid-tones
            consistency_score = 1.0 - min(std_intensity / 50, 1.0)  # Prefer low variation
            
            # Bonus for bottom positions (traditional logo placement)
            position_bonus = 0.3 if 'bottom' in position_name else 0.0
            
            total_score = intensity_score * 0.4 + consistency_score * 0.4 + position_bonus
            
            logger.debug(f"Position {position_name} at ({x}, {y}): score {total_score:.3f}")
            
            if total_score > best_score:
                best_score = total_score
                best_position = (position_name, x, y)
        
        if best_position:
            position_name, x, y = best_position
            logger.info(f"Selected position: {position_name} at ({x}, {y}) with score {best_score:.3f}")
            return (x, y)
        
        # Fallback to bottom-left with margin
        fallback_x, fallback_y = 20, img_height - logo_height - 20
        logger.info(f"Using fallback position: bottom-left at ({fallback_x}, {fallback_y})")
        return (fallback_x, fallback_y)
    
    def remove_old_logo(self, image: Image.Image, logo_position: tuple):
        """Remove/clear the old logo from its position."""
        x, y, w, h = logo_position
        
        # Create a copy to work with
        result_image = image.copy()
        
        # Extract the old logo region
        logo_region = image.crop((x, y, x + w, y + h))
        
        # Try to fill with surrounding background color
        # Sample colors from around the logo area (expanding outward)
        margin = 10
        sample_regions = []
        
        # Sample from left, right, top, bottom of logo
        if x - margin >= 0:
            sample_regions.append((x - margin, y, margin, h))  # Left
        if x + w + margin <= image.width:
            sample_regions.append((x + w, y, margin, h))  # Right
        if y - margin >= 0:
            sample_regions.append((x, y - margin, w, margin))  # Top
        if y + h + margin <= image.height:
            sample_regions.append((x, y + h, w, margin))  # Bottom
        
        # Calculate average background color
        if sample_regions:
            all_pixels = []
            for sx, sy, sw, sh in sample_regions:
                sample = image.crop((sx, sy, sx + sw, sy + sh))
                sample_array = np.array(sample)
                all_pixels.extend(sample_array.reshape(-1, sample_array.shape[-1]))
            
            if all_pixels:
                avg_color = tuple(map(int, np.mean(all_pixels, axis=0)))
            else:
                avg_color = (255, 255, 255)  # White fallback
        else:
            avg_color = (255, 255, 255)  # White fallback
        
        # Fill the old logo area with background color
        from PIL import ImageDraw
        draw = ImageDraw.Draw(result_image)
        draw.rectangle([x, y, x + w, y + h], fill=avg_color)
        
        logger.info(f"Removed old logo from ({x}, {y}) and filled with color {avg_color}")
        return result_image
    
    def _find_logo_in_corners(self, image: Image.Image, strict_threshold: float = 0.25):
        """Try to find logo in common corners with flexible similarity checking."""
        # Try different sizes for the logo search area
        logo_sizes = [
            (self.old_logo.width, self.old_logo.height),  # Original size
            (int(self.old_logo.width * 0.5), int(self.old_logo.height * 0.5)),  # Half size
            (int(self.old_logo.width * 0.75), int(self.old_logo.height * 0.75)),  # 3/4 size
            (int(self.old_logo.width * 1.25), int(self.old_logo.height * 1.25)),  # 1.25x size
        ]
        
        corners = ['bottom-left', 'bottom-right', 'top-left', 'top-right']
        
        best_match = None
        best_similarity = 0
        
        for w, h in logo_sizes:
            if w <= 0 or h <= 0:
                continue
                
            corner_positions = [
                ('bottom-left', 0, image.height - h, w, h),
                ('bottom-right', image.width - w, image.height - h, w, h),
                ('top-left', 0, 0, w, h),
                ('top-right', image.width - w, 0, w, h)
            ]
            
            for corner_name, x, y, check_w, check_h in corner_positions:
                if x >= 0 and y >= 0 and x + check_w <= image.width and y + check_h <= image.height:
                    # Extract region
                    region = image.crop((x, y, x + check_w, y + check_h))
                    
                    try:
                        # Convert both to RGB for comparison
                        region_rgb = region.convert('RGB')
                        logo_rgb = self.old_logo.resize((check_w, check_h), Image.Resampling.LANCZOS).convert('RGB')
                        
                        # Use OpenCV for template matching on the cropped region
                        region_cv = cv2.cvtColor(np.array(region_rgb), cv2.COLOR_RGB2BGR)
                        logo_cv = cv2.cvtColor(np.array(logo_rgb), cv2.COLOR_RGB2BGR)
                        
                        # Calculate similarity using normalized cross correlation
                        result = cv2.matchTemplate(region_cv, logo_cv, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(result)
                        
                        if max_val > best_similarity:
                            best_similarity = max_val
                            best_match = (corner_name, x, y, check_w, check_h, max_val)
                        
                        logger.debug(f"Checked {corner_name} corner (size {check_w}x{check_h}): similarity {max_val:.3f}")
                            
                    except Exception as e:
                        logger.debug(f"Error checking {corner_name} corner: {e}")
                        continue
        
        if best_match and best_similarity > strict_threshold:
            corner_name, x, y, w, h, similarity = best_match
            logger.info(f"Found logo in {corner_name} corner with similarity {similarity:.3f}")
            return (x, y, w, h)
        
        return None
    
    def _remove_overlapping_boxes(self, boxes: List[Tuple[int, int, int, int]], 
                                 overlap_threshold: float = 0.5):
        """Remove overlapping bounding boxes."""
        if not boxes:
            return []
        
        # Simple implementation - remove boxes that are too close
        filtered_boxes = []
        for box in boxes:
            x1, y1, w1, h1 = box
            is_unique = True
            
            for existing_box in filtered_boxes:
                x2, y2, w2, h2 = existing_box
                
                # Check if boxes overlap significantly
                overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
                overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
                overlap_area = overlap_x * overlap_y
                
                box1_area = w1 * h1
                box2_area = w2 * h2
                
                if overlap_area > overlap_threshold * min(box1_area, box2_area):
                    is_unique = False
                    break
            
            if is_unique:
                filtered_boxes.append(box)
        
        return filtered_boxes
    
    def generate_filename(self, url: str, section_id: int, report_id: int, index: int = 0):
        """Generate filename for downloaded image."""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        path = parsed_url.path
        extension = Path(path).suffix.lower()
        
        if not extension or extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            extension = '.jpg'
        
        filename = f"report_{report_id}_section_{section_id}_img_{index}{extension}"
        return filename
    
    def upload_file_to_s3(self, local_file_path: str, s3_key: str) -> bool:
        """Upload a single file to S3."""
        if not self.s3_client:
            logger.warning("S3 client not initialized - skipping upload")
            return False
        
        try:
            # Upload the file
            self.s3_client.upload_file(
                local_file_path, 
                self.s3_config['bucket_name'], 
                s3_key,
                ExtraArgs={'ContentType': self._get_content_type(local_file_path)}
            )
            logger.info(f"✅ Uploaded to S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"❌ Failed to upload {local_file_path} to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading {local_file_path}: {e}")
            return False
    
    def _get_content_type(self, file_path: str) -> str:
        """Get the appropriate content type for a file."""
        extension = Path(file_path).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def upload_processed_images_to_s3(self, image_db_map=None) -> dict:
        """Upload all processed images to S3 and update DB URLs if mapping provided."""
        if not self.s3_client:
            logger.info("S3 client not available - skipping S3 upload")
            return {'uploaded': 0, 'failed': 0, 'skipped': 'S3 not configured'}

        upload_stats = {'uploaded': 0, 'failed': 0, 'files': []}

        logger.info("🔄 Starting S3 upload of processed images...")

        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, self.download_dir)
                    s3_key = f"{self.s3_config['folder_prefix']}{relative_path.replace(os.sep, '/')}"
                    # Upload the file
                    if self.upload_file_to_s3(local_path, s3_key):
                        upload_stats['uploaded'] += 1
                        upload_stats['files'].append({
                            'local_path': local_path,
                            's3_key': s3_key,
                            'status': 'uploaded'
                        })
                        # If mapping info is available, update DB
                        if image_db_map:
                            # Try both absolute and normalized paths to find the mapping
                            abs_local_path = os.path.abspath(local_path)
                            info = image_db_map.get(abs_local_path) or image_db_map.get(local_path)
                            
                            if info:
                                section_id, old_url = info['section_id'], info['old_url']
                                
                                # Construct S3 URL - use standard format for us-east-1, regional for others
                                if self.s3_config['region_name'] == 'us-east-1':
                                    s3_url = f"https://{self.s3_config['bucket_name']}.s3.amazonaws.com/{s3_key}"
                                else:
                                    s3_url = f"https://{self.s3_config['bucket_name']}.s3.{self.s3_config['region_name']}.amazonaws.com/{s3_key}"
                                
                                logger.info(f"🔄 Updating DB: section {section_id} | {old_url} -> {s3_url}")
                                self.update_image_url_in_db(section_id, old_url, s3_url)
                            else:
                                logger.warning(f"⚠️ No DB mapping found for {local_path} or {abs_local_path}")
                                # Debug: print available mappings
                                if image_db_map:
                                    logger.debug(f"Available mappings: {list(image_db_map.keys())}")
                        else:
                            logger.debug("No image_db_map provided - skipping DB update")
                    else:
                        upload_stats['failed'] += 1
                        upload_stats['files'].append({
                            'local_path': local_path,
                            's3_key': s3_key,
                            'status': 'failed'
                        })

        logger.info(f"📊 S3 Upload Summary: {upload_stats['uploaded']} uploaded, {upload_stats['failed']} failed")
        return upload_stats
    
    def process_all(self, report_id: Optional[int] = None):
        """Complete process: cleanup, download, and replace logos."""
        logger.info("Starting complete image processing workflow")
        
        # Step 1: Cleanup old data
        self.cleanup_old_data()
        
        # Step 2: Fetch sections from database
        logger.info("Fetching report sections from database...")
        sections = self.fetch_report_sections(report_id)
        
        results = {
            'total_sections': len(sections),
            'sections_with_images': 0,
            'total_images_found': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'logo_replacements': 0,
            'processed_files': [],
            'files_with_logo_replaced': [],
            'files_without_old_logo': []
        }
        # Map local image path to DB info for S3 update
        image_db_map = {}
        
        # Step 3: Process each section
        for section in sections:
            section_id = section['id']
            report_id = section['report_id']
            heading = section['heading'] or f"Section_{section_id}"
            content = section['content']
            
            # Extract image URLs
            image_objects = self.extract_image_urls(content)
            
            if image_objects:
                results['sections_with_images'] += 1
                results['total_images_found'] += len(image_objects)
                
                logger.info(f"Processing section {section_id} (Report {report_id}): {heading}")
                logger.info(f"Found {len(image_objects)} images")
                
                for idx, img_obj in enumerate(image_objects):
                    url = img_obj['url']
                    filename = self.generate_filename(url, section_id, report_id, idx)
                    subfolder = f"by_report/report_{report_id}"

                    # Download image
                    downloaded_path = self.download_image(url, filename, subfolder)

                    if downloaded_path:
                        results['successful_downloads'] += 1

                        # Track for S3/DB update
                        image_db_map[os.path.abspath(downloaded_path)] = {
                            'section_id': section_id,
                            'old_url': url
                        }

                        # Try to replace logo (only if old logo is actually found)
                        if self.find_and_replace_logo(downloaded_path):
                            results['logo_replacements'] += 1
                            results['files_with_logo_replaced'].append(Path(downloaded_path).name)
                            logger.info(f"✅ Logo replaced in: {Path(downloaded_path).name}")
                        else:
                            results['files_without_old_logo'].append(Path(downloaded_path).name)
                            logger.info(f"ℹ️  No old logo found in: {Path(downloaded_path).name} (skipped logo replacement)")

                        results['processed_files'].append(downloaded_path)
                    else:
                        results['failed_downloads'] += 1
        
        # Step 4: Upload processed images to S3 and update DB URLs
        logger.info("🔄 Starting S3 upload...")
        s3_results = self.upload_processed_images_to_s3(image_db_map)
        results['s3_upload'] = s3_results
        return results
    
    def print_summary(self, results):
        """Print processing summary."""
        print("\n" + "="*60)
        print("STREAMLINED IMAGE PROCESSING SUMMARY")
        print("="*60)
        print(f"Total sections processed: {results['total_sections']}")
        print(f"Sections with images: {results['sections_with_images']}")
        print(f"Total images found: {results['total_images_found']}")
        print(f"Successful downloads: {results['successful_downloads']}")
        print(f"Failed downloads: {results['failed_downloads']}")
        print(f"Logo replacements: {results['logo_replacements']}")
        print(f"Images without old logo: {len(results.get('files_without_old_logo', []))}")
        print(f"Output directory: {self.download_dir.absolute()}")
        
        # S3 upload summary
        if 's3_upload' in results:
            s3_info = results['s3_upload']
            if isinstance(s3_info, dict) and 'uploaded' in s3_info:
                print(f"S3 uploads: {s3_info['uploaded']} successful, {s3_info['failed']} failed")
            else:
                print(f"S3 upload: {s3_info}")
        
        if results.get('files_with_logo_replaced'):
            print(f"\n✅ Files with logo REPLACED:")
            for filename in results['files_with_logo_replaced']:
                print(f"  🔄 {filename}")
        
        if results.get('files_without_old_logo'):
            print(f"\nℹ️  Files WITHOUT old logo (no replacement needed):")
            for filename in results['files_without_old_logo']:
                print(f"  📁 {filename}")
        
        if results['processed_files']:
            print(f"\n📊 All processed files:")
            for file_path in results['processed_files']:
                filename = Path(file_path).name
                status = "🔄" if filename in results.get('files_with_logo_replaced', []) else "📁"
                print(f"  {status} {filename}")


def process_all_reports():
    """Convenience function to process all reports without any prompts."""
    try:
        processor = StreamlinedImageProcessor()
        print("🚀 Starting batch processing of ALL reports...")
        
        # Process ALL reports
        results = processor.process_all(report_id=None)
        
        # Print summary
        processor.print_summary(results)
        
        # Return results for programmatic use
        return results
        
    except Exception as e:
        logger.error(f"Error processing all reports: {e}")
        print(f"❌ Error: {e}")
        return None


def main():
    """Main function."""
    print("Streamlined Image Processor with Logo Replacement")
    print("=" * 55)
    print("Processing ALL reports in the database...")
    print("This will:")
    print("1. Clean up old processed images")
    print("2. Download ALL images from ALL reports")
    print("3. Replace old logos with new logos")
    print("-" * 55)
    
    try:
        processor = StreamlinedImageProcessor()
        
        # Process ALL reports (no specific report ID)
        results = processor.process_all(report_id=None)
        
        # Print summary
        processor.print_summary(results)
        
        print(f"\n🎉 Processing completed!")
        print(f"✅ Downloaded: {results['successful_downloads']} images")
        print(f"🔄 Logo replacements: {results['logo_replacements']}")
        print(f"📁 Files saved to: {processor.download_dir.absolute()}")
        
        # S3 upload summary
        if 's3_upload' in results:
            s3_info = results['s3_upload']
            if isinstance(s3_info, dict) and 'uploaded' in s3_info:
                if s3_info['uploaded'] > 0:
                    print(f"☁️ S3 uploads: {s3_info['uploaded']} files uploaded successfully")
                if s3_info['failed'] > 0:
                    print(f"⚠️ S3 upload failures: {s3_info['failed']} files failed to upload")
            else:
                print(f"ℹ️ S3 upload: {s3_info}")
        
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
