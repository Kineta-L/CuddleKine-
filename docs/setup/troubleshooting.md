# Troubleshooting

## App Opens but Generation Fails

Check:

- the selected provider is configured
- the API key is valid
- the provider account has credit
- the backend status is connected
- the provider supports the selected generation mode

## Agnes Does Not Follow Reference Image

Reference-image generation requires the image to be accessible by the Agnes API.

Check:

- Tencent COS is configured
- the image upload succeeded
- the signed URL is valid
- Agnes provider is selected
- the prompt is short and does not fight the reference image

## Server Disconnected Without Sending a Response

This usually means the local backend crashed or was restarted.

Try:

- close and reopen CuddleKine
- check whether another process is using port `8765`
- run from source and inspect backend logs if you are a developer

## Replicate Returns 401

The API token is missing or invalid. Paste a valid Replicate token in Settings.

## Replicate Returns 402

The Replicate account does not have enough credit for the selected model.

## Tencent COS Returns InvalidAccessKeyId

The SecretId is wrong, deleted, disabled, or belongs to another Tencent Cloud account.

## Local ComfyUI Quality Is Poor

ComfyUI output depends heavily on the checkpoint, LoRA, workflow, prompts, and GPU setup. In this project, ComfyUI is mainly useful for drafts. For final plush sample images, use Agnes or another cloud image provider.
