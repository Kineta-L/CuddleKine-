# Configure Tencent Cloud COS

Tencent Cloud COS is used as a private image bridge. It lets cloud image models read reference images that were originally uploaded into the local CuddleKine desktop app.

## Why COS Is Needed

Local files such as:

```text
C:\Users\...\reference.png
```

cannot be read directly by cloud model APIs. CuddleKine solves this by:

1. Uploading the reference image to a private COS bucket.
2. Creating a temporary signed URL.
3. Sending that signed URL to the selected cloud model.

## Create a Bucket

1. Open Tencent Cloud Console.
2. Go to Object Storage COS.
3. Create a bucket.
4. Choose a region close to your users, such as `ap-guangzhou` or `ap-shanghai`.
5. Keep the bucket private.

Recommended example:

```text
Bucket: cuddlekine-images-<appid>
Region: ap-guangzhou
Access: private
```

## Create API Credentials

1. Open Tencent Cloud Access Management.
2. Create or use a CAM user for CuddleKine.
3. Create a SecretId and SecretKey.
4. Grant only the permissions needed for COS object upload/read signing.

Recommended security approach:

- Use a dedicated key for CuddleKine.
- Do not use the root account key.
- Rotate the key if it is exposed.

## Fill Settings in CuddleKine

Open:

```text
Settings -> Storage / Tencent COS
```

Fill:

- COS SecretId
- COS SecretKey
- bucket name
- region
- signed URL expiry seconds

Then test upload/signing from Settings.

## Common COS Errors

### InvalidAccessKeyId

The SecretId does not exist or was copied incorrectly. Create a new key or paste it again.

### SignatureDoesNotMatch

The SecretKey, bucket, region, or request signing configuration is incorrect.

### AccessDenied

The key does not have permission to upload or read/sign objects in the bucket.

### Model Still Cannot Read the Image

Check:

- the signed URL has not expired
- the bucket region is correct
- the model provider can access Tencent COS URLs
- the file was uploaded successfully
