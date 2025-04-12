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

