# Configure Model Providers

CuddleKine supports multiple image-generation providers because different studios may prefer different model quality, cost, speed, and regional availability.

## Provider Selection

Open CuddleKine and go to:

```text
Settings -> Model Provider
```

Recommended choices:

- Agnes: best current fit for plush toy sample image generation in this project.
- OpenAI / GPT image models: good for high-quality visual generation when available.
- Replicate: useful for testing hosted open models.
- ComfyUI: useful for local experiments and draft generation.
- Mock: useful for app testing without spending API credits.

## Agnes

Required:

- Agnes API key
- Agnes base URL, if different from the default shown in Settings

For reference-image generation, configure Tencent Cloud COS so CuddleKine can pass a temporary image URL to Agnes.

## OpenAI

Required:

- OpenAI API key
- an image-capable model name supported by your account

OpenAI image generation may support reference images depending on the selected model and API capability.

## Replicate

Required:

- Replicate API token
- model identifier or version

Some Replicate models charge per generation or require credit. If you see an insufficient-credit error, add credit in the Replicate dashboard.

## ComfyUI

Required:

- running local ComfyUI server
- ComfyUI API URL, usually `http://127.0.0.1:8188`
- ComfyUI input directory if using local reference uploads

ComfyUI is kept as a local/draft provider. In this project, final-quality plush sample images are usually better with cloud models.

## API Key Safety

- Do not paste API keys into GitHub issues or public screenshots.
- Do not commit local settings files.
- Revoke and recreate a key if it was exposed.
- Use a provider account with spending limits when possible.
