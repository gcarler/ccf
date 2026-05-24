import sys

import boto3
from botocore.client import Config


def test_seaweed_s3():
    s3_endpoint = "http://localhost:8333"
    access_key = "ccf"
    secret_key = "LXuAMDMb7Wwwqt3NVzeLpVO7FVF0Fswx"
    bucket_name = "ccf-uploads"

    print(f"Connecting to {s3_endpoint}...")
    s3 = boto3.resource(
        "s3",
        endpoint_url=s3_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    try:
        # 1. Ensure bucket exists
        bucket = s3.Bucket(bucket_name)
        if bucket.creation_date:
            print(f"Bucket '{bucket_name}' already exists.")
        else:
            print(f"Creating bucket '{bucket_name}'...")
            s3.create_bucket(Bucket=bucket_name)

        # 2. Upload a test file
        test_content = b"SeaweedFS S3 Quality Test - SUCCESS"
        test_key = "quality_test.txt"
        print(f"Uploading '{test_key}'...")
        s3.Object(bucket_name, test_key).put(Body=test_content)

        # 3. Download and verify
        print(f"Downloading '{test_key}' to verify...")
        obj = s3.Object(bucket_name, test_key)
        downloaded_content = obj.get()["Body"].read()

        if downloaded_content == test_content:
            print("QUALITY CHECK PASSED: Content matches perfectly.")
        else:
            print("QUALITY CHECK FAILED: Content mismatch.")
            sys.exit(1)

        # 4. Clean up
        print("Cleaning up test file...")
        s3.Object(bucket_name, test_key).delete()
        print("Clean up complete.")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    test_seaweed_s3()
