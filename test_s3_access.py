#!/usr/bin/env python3
"""
Simple S3 Test Script to verify access
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_s3_access():
    """Test S3 access with current credentials."""
    
    # S3 configuration from .env
    s3_config = {
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'region_name': os.getenv('AWS_REGION', 'us-east-1'),
        'bucket_name': os.getenv('S3_BUCKET_NAME')
    }
    
    print(f"Testing S3 access...")
    print(f"Bucket: {s3_config['bucket_name']}")
    print(f"Region: {s3_config['region_name']}")
    print(f"Access Key: {s3_config['aws_access_key_id'][:8]}...")
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=s3_config['aws_access_key_id'],
            aws_secret_access_key=s3_config['aws_secret_access_key'],
            region_name=s3_config['region_name']
        )
        
        # Test 1: Get caller identity (if STS is available)
        try:
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=s3_config['aws_access_key_id'],
                aws_secret_access_key=s3_config['aws_secret_access_key'],
                region_name=s3_config['region_name']
            )
            identity = sts_client.get_caller_identity()
            print(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        except Exception as e:
            print(f"⚠️ STS Access: {e}")
        
        # Test 2: List buckets
        try:
            response = s3_client.list_buckets()
            print(f"✅ Can list buckets: Found {len(response['Buckets'])} buckets")
        except Exception as e:
            print(f"❌ Cannot list buckets: {e}")
        
        # Test 3: Head bucket (check if specific bucket exists and is accessible)
        try:
            s3_client.head_bucket(Bucket=s3_config['bucket_name'])
            print(f"✅ Can access bucket: {s3_config['bucket_name']}")
        except Exception as e:
            print(f"❌ Cannot access bucket: {e}")
        
        # Test 4: List objects in bucket
        try:
            response = s3_client.list_objects_v2(
                Bucket=s3_config['bucket_name'],
                MaxKeys=1
            )
            print(f"✅ Can list objects in bucket")
        except Exception as e:
            print(f"❌ Cannot list objects: {e}")
        
        # Test 5: Try to put a small test object
        try:
            test_key = "test-access/test-file.txt"
            test_content = "This is a test file to verify S3 write access."
            
            s3_client.put_object(
                Bucket=s3_config['bucket_name'],
                Key=test_key,
                Body=test_content.encode('utf-8'),
                ContentType='text/plain'
            )
            print(f"✅ Can write to S3: Successfully uploaded test file")
            
            # Clean up test file
            try:
                s3_client.delete_object(Bucket=s3_config['bucket_name'], Key=test_key)
                print(f"✅ Can delete from S3: Test file cleaned up")
            except Exception as e:
                print(f"⚠️ Could not delete test file: {e}")
                
        except Exception as e:
            print(f"❌ Cannot write to S3: {e}")
            print("This is the main issue preventing uploads!")
        
    except Exception as e:
        print(f"❌ Failed to create S3 client: {e}")

if __name__ == "__main__":
    test_s3_access()
