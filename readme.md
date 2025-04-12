# 🖼️ Lambda Image Thumbnail Generator

This AWS Lambda function automatically creates thumbnails when an image is uploaded to an S3 bucket.

## ✅ What It Does

- Triggers when an image is uploaded to the `source_image/` folder in S3 bucket
- Handles filenames with spaces and special characters (like "Screenshot 2025-03-07 030749.png")
- Creates a folder under `processed_image/` with a sanitized name and random suffix
- Generates resized thumbnails: 200px, 300px, 500px, and 1000px wide
- Maintains the original image format (JPG/JPEG or PNG)
- Preserves aspect ratio (height adjusts automatically)
- Returns paths of all generated files as a JSON response

## 📁 Folder Structure

The S3 bucket `prince-s3-v1` contains:

- `source_image/` - Upload your images here to trigger processing
- `processed_image/` - Contains generated thumbnails in subfolders

For example, if you upload `source_image/vacation photo.jpg`, it creates:
- processed_image/vacation_photo_a1b2c3d4/
  - 200_vacation_photo_a1b2c3d4.jpg
  - 300_vacation_photo_a1b2c3d4.jpg
  - 500_vacation_photo_a1b2c3d4.jpg
  - 1000_vacation_photo_a1b2c3d4.jpg

## 🐳 Setting Up Pillow Layer Using Docker

Since Pillow requires native dependencies, we build a Lambda-compatible layer using Docker:

### 1. Create a Dockerfile

```Dockerfile
# Use AWS Lambda Python 3.9 base image
FROM public.ecr.aws/lambda/python:3.9
# Set working directory
WORKDIR /var/task
# Install zip utility
RUN yum install -y zip
# Create layer directory
RUN mkdir -p python
# Install Pillow into the layer directory
RUN pip install Pillow -t python
# Zip the layer contents
RUN zip -r pillow-layer.zip python
```

### 2. Build and Extract the Layer

Run these commands to build the Docker image and extract the layer:

```bash
# Build the Docker image
docker build -t pillow-layer .

# Create a container from the image
docker create --name temp-pillow-layer pillow-layer 

# Copy the layer zip from the container
docker cp temp-pillow-layer:/var/task/pillow-layer.zip ./pillow-layer.zip

# Remove the temporary container
docker rm temp-pillow-layer
```

### 3. Create Lambda Layer

- Go to AWS Lambda > Layers > Create Layer
- Upload the `pillow-layer.zip` file
- Set the compatible runtime to **Python 3.9**
- Attach this layer to your Lambda function

## 🔧 Lambda Function Setup

1. Create a new Lambda function:
   - Runtime: **Python 3.9**
   - Architecture: **x86_64**
   - Timeout: **30 seconds** or more
   - Memory: **256 MB** or more

2. Add the Pillow layer to your function

3. Configure an S3 trigger:
   - Bucket: **prince-s3-v1**
   - Event type: **Object Created (All)**
   - Prefix: **source_image/**

4. Permissions:
   - Ensure your Lambda execution role has permissions to:
     - Read from `source_image/` in your S3 bucket
     - Write to `processed_image/` in your S3 bucket
     - Create CloudWatch logs

## 📝 Testing

1. Upload any JPG, JPEG, or PNG file to the `source_image/` folder in your S3 bucket
2. Check CloudWatch logs to verify processing
3. Look for new thumbnails in the corresponding subfolder under `processed_image/`

## 🔍 Troubleshooting

- If thumbnails aren't generated, check the Lambda function logs in CloudWatch
- Verify S3 bucket permissions and Lambda execution role
- Ensure the Pillow layer is correctly attached to your Lambda function
