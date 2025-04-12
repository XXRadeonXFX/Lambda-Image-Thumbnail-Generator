import boto3
import os
import tempfile
import uuid
import urllib.parse
from PIL import Image

s3 = boto3.client('s3')

def compress_and_create_thumbnail(image_path, output_path, width, original_ext, quality=70):
    img = Image.open(image_path)
    # Resize while maintaining aspect ratio
    original_width, original_height = img.size
    aspect_ratio = original_height / original_width
    new_height = int(width * aspect_ratio)
    resized_img = img.resize((width, new_height), Image.Resampling.LANCZOS)
    
    # Save in appropriate format
    if original_ext.lower() == ".png":
        resized_img.save(output_path, format="PNG", optimize=True)
    else:
        if resized_img.mode in ("RGBA", "P"):
            resized_img = resized_img.convert("RGB")
        resized_img.save(output_path, format="JPEG", quality=quality, optimize=True)

def sanitize_filename(filename):
    """Create a safe version of the filename for S3 keys"""
    # Replace problematic characters with underscores
    return filename.replace(' ', '_').replace('(', '_').replace(')', '_')

def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    
    # Properly decode URL-encoded object key
    object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    # ✅ Process only files in 'source_image/' folder
    if not object_key.startswith("source_image/"):
        print(f"Skipping non-source_image file: {object_key}")
        return {'statusCode': 200, 'body': f"Skipped: {object_key}"}
    
    # ✅ Skip non-image files
    file_ext = os.path.splitext(object_key)[1].lower()
    if file_ext not in [".jpg", ".jpeg", ".png"]:
        print(f"Skipping unsupported file type: {file_ext}")
        return {'statusCode': 200, 'body': f"Unsupported file type: {file_ext}"}
    
    # Get original filename and create sanitized versions
    file_name = os.path.basename(object_key)
    name_without_ext = os.path.splitext(file_name)[0]
    
    # Generate a unique ID to avoid collisions
    random_id = uuid.uuid4().hex[:8]
    
    # Create a sanitized base filename that's safe for S3
    sanitized_name = sanitize_filename(name_without_ext)
    base_file_name = f"{sanitized_name}_{random_id}"
    
    save_ext = ".png" if file_ext.lower() == ".png" else ".jpg"
    folder_path = f"processed_image/{base_file_name}/"
    
    # Use unique temporary paths to avoid collisions
    temp_dir = tempfile.mkdtemp()
    local_input_path = os.path.join(temp_dir, file_name)
    
    try:
        # ✅ Download original file from S3
        s3.download_file(bucket_name, object_key, local_input_path)
        
        processed_files = []
        sizes = [200, 300, 500, 1000]
        
        for size in sizes:
            output_file_name = f"{size}_{base_file_name}{save_ext}"
            local_output_path = os.path.join(temp_dir, output_file_name)
            s3_key = f"{folder_path}{output_file_name}"
            
            # Skip if already processed (extra safety)
            try:
                s3.head_object(Bucket=bucket_name, Key=s3_key)
                print(f"Skipping already processed image: {s3_key}")
                continue
            except s3.exceptions.ClientError as e:
                if e.response['Error']['Code'] != "404":
                    raise
            
            # ✅ Create thumbnail and upload
            compress_and_create_thumbnail(local_input_path, local_output_path, size, file_ext)
            s3.upload_file(local_output_path, bucket_name, s3_key)
            processed_files.append(f"s3://{bucket_name}/{s3_key}")
            
            # Clean up temporary file
            if os.path.exists(local_output_path):
                os.remove(local_output_path)
                
            print(f"Uploaded: {s3_key}")
        
        # Clean up input file
        if os.path.exists(local_input_path):
            os.remove(local_input_path)
        
        # Try to remove temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass
            
        response = {
            "original_file": f"s3://{bucket_name}/{object_key}",
            "processed_files": processed_files,
            "original_filename": file_name,
            "sanitized_filename": f"{base_file_name}{save_ext}"
        }
        
        print("✅ Processing complete")
        return {
            'statusCode': 200,
            'body': str(response)
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }
