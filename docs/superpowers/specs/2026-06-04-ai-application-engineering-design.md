# CuddleKine AI Application Engineering Design

Date: 2026-06-04

## Goal

Upgrade CuddleKine from a prompt-driven image generation tool into an AI-assisted plush toy sampling workflow.

Designers should not write model prompts as their main task. The application should understand customer materials, produce a structured plush toy brief, ask follow-up questions, let the designer confirm or edit the brief, and then build provider-specific prompts internally.

## Assumptions

- Phase 1 focuses on a useful engineering loop, not model fine-tuning or LoRA training.
- OpenAI vision can be used when configured; otherwise the system falls back to deterministic rule-based extraction.
- Designers still make the final decision before sample/final generation.
- Existing providers remain: ComfyUI, OpenAI, Replicate, and mock.
- Existing local-first behavior remains. API keys, generated outputs, SQLite data, and local settings stay out of Git.

## Success Criteria

- An order can analyze uploaded materials and produce a structured brief.
- The brief contains business fields, manufacturing suggestions, risk notes, and customer follow-up questions.
- Designers can edit and confirm the brief without seeing English prompts by default.
- Image generation can use a confirmed brief to build provider-specific prompts.
- Generation records can be traced back to source materials, brief, prompt builder version, final prompt, provider prompt, and model.
- Draft generation remains possible before confirmation; sample/final generation requires a confirmed brief.
- Existing build checks still pass: frontend build, backend compile, and Tauri cargo check.

## Approaches Considered

### Recommended: Layered AI Workflow

Add bounded backend services for material understanding, brief building, question generation, prompt building, and manufacturing adaptation. Keep the current order, material, brief, and generation tables, extending them with traceability fields.

This is the best fit because it improves product behavior without replacing the current app.

### Alternative: Single Large Agent Endpoint

Create one endpoint that takes all order data and returns the final prompt. This is faster to build, but makes debugging hard and hides important intermediate artifacts from designers.

Rejected for Phase 1 because CuddleKine needs trust, editability, and traceability.

### Alternative: UI-Only Prompt Helper

Only improve frontend fields and prompt templates. This is low-risk, but it keeps the product prompt-centric and does not solve AI engineering traceability.

Rejected because it does not match the product direction.

## Chosen Architecture

Phase 1 adds a backend pipeline:

1. Material Understanding Agent
2. Manufacturing Adapter
3. Brief Builder
4. Question Agent
5. Prompt Builder
6. Generation Trace Recorder

The frontend exposes this as a designer workflow:

1. Upload customer materials.
2. Click AI analyze.
3. Review structured brief.
4. Review follow-up questions and copy them to the customer if needed.
5. Edit and confirm the brief.
6. Generate sample images using provider-specific prompts built internally.

## Backend Services

### `material_understanding_agent.py`

Purpose: Convert uploaded images, OCR text, and designer notes into normalized observations.

Inputs:

- Material records for an order.
- File paths for image materials.
- OCR text and notes.
- Provider settings.

Outputs:

- Source type.
- Detected subject.
- Visual feature JSON.
- AI or rule-based description.
- Processing status.

The implementation should use OpenAI vision when configured. If no vision model is configured, it should produce a conservative rule-based result from material type, filename, OCR text, and notes.

### `manufacturing_adapter.py`

Purpose: Convert real-world or illustrated features into plush-manufacturable language.

Examples:

- Real hair becomes plush hair blocks, embroidered hair lines, or layered fabric pieces.
- Small text becomes simplified symbols or color blocks unless explicitly required.
- Metal, glass, and hard objects become fabric accessories, applique, or embroidery.
- Complex prints become simplified embroidery, applique, or color panels.

### `brief_builder.py`

Purpose: Build a fixed structured brief schema from material understanding results.

Core fields:

- `order_intent`
- `source_type`
- `toy_category`
- `character_identity`
- `target_height`
- `body_proportions`
- `head_features`
- `face_features`
- `clothing`
- `colors`
- `materials`
- `accessories`
- `key_features_to_preserve`
- `allowed_simplifications`
- `forbidden_changes`
- `manufacturing_suggestions`
- `pending_questions`
- `risk_notes`

### `question_agent.py`

Purpose: Generate customer follow-up questions based on missing or risky fields.

Questions should be short, customer-facing, and copyable.

### `prompt_builder.py`

Purpose: Convert confirmed structured briefs into provider-specific prompts.

Layers:

1. Global plush toy rules.
2. Character information from brief.
3. Current task: main view, front, side, back, or local modification.
4. Provider-specific formatting.

The prompt builder should expose a preview endpoint for advanced inspection, but designers should not need to edit prompts in normal use.

## Database Changes

Use additive schema migration in `backend/app/database.py` so existing local SQLite databases continue to work.

### `materials`

Add:

- `source_type`
- `detected_subject`
- `image_width`
- `image_height`
- `ai_description`
- `visual_features_json`
- `processing_status`

### `briefs`

Add:

- `source_material_ids`
- `source_type`
- `pending_questions`
- `risk_notes`
- `designer_edits`
- `ai_model_used`
- `prompt_version`

Existing `structured_content`, `missing_info`, `conflicts`, and `is_confirmed` remain.

### `generation_records`

Add:

- `brief_id`
- `prompt_builder_version`
- `final_prompt`
- `provider_prompt`
- `source_material_ids`
- `quality_status`
- `review_notes`

Existing `prompt` and `negative_prompt` remain for compatibility. New prompt fields are clearer trace artifacts.

### `orders`

Add:

- `brief_status`
- `confirmed_brief_id`
- `source_summary`
- `customer_question_status`

Existing `status` remains the broad workflow status.

## API Design

Add:

- `POST /api/materials/{material_id}/analyze`
- `POST /api/orders/{order_id}/analyze-materials`
- `POST /api/orders/{order_id}/briefs/generate`
- `POST /api/orders/{order_id}/briefs/{brief_id}/confirm`
- `POST /api/orders/{order_id}/questions/generate`
- `POST /api/prompts/preview`

Update:

- `POST /api/generation/generate`

New generation request fields:

- `brief_id`
- `source_material_ids`
- `prompt_builder_version`
- `use_confirmed_brief_only`

Rule:

- `draft` generation can run without a confirmed brief.
- `sample` and `final` generation require a confirmed brief unless explicitly overridden by developer-only code, which will not be exposed in the UI.

## Frontend Design

Order detail becomes the AI brief workbench:

- Materials panel with upload and analysis status.
- AI analysis button.
- Structured brief editor using Chinese business fields.
- Follow-up questions panel with copy action.
- Risk notes and manufacturing suggestions panel.
- Confirm brief action.
- Advanced prompt preview hidden behind an explicit button.

Generation panel changes:

- Show confirmed brief status before generation.
- Disable sample/final generation until brief is confirmed.
- Keep provider/model selection.
- Show trace information for selected generation: brief version, prompt builder version, provider, and source materials.
- Add generation quality marking in Phase 1 if it is small enough to fit safely; otherwise leave the database fields ready for Phase 2 UI.

## Error Handling

- If no materials exist, analysis returns a clear 400 error.
- If AI provider is not configured, analysis falls back to rule-based mode and marks `ai_model_used` as `rule-based`.
- If a brief is not confirmed, sample/final generation returns a clear 400 error.
- If prompt preview fails, generation should not start.
- Provider errors continue to be stored in `generation_records.error_message`.

## Testing

Backend:

- Compile check with `python -m compileall backend\app`.
- Add focused tests only if the current repo has a test framework; otherwise verify endpoints manually through direct calls.

Frontend:

- Run `npm.cmd run build`.
- Verify TypeScript types after API client changes.

Tauri:

- Run `cargo check` in `desktop/src-tauri`.

Manual acceptance:

- Create or open an order.
- Upload a reference material.
- Analyze materials.
- Confirm or edit brief.
- Generate draft without confirmation.
- Confirm brief.
- Generate sample using confirmed brief.
- Inspect generation record trace fields.

## Out Of Scope For Phase 1

- LoRA training.
- Large analytics dashboard.
- Full customer-facing portal.
- Automatic three-view consistency scoring.
- Billing integration.
- Multi-user authentication.

## Implementation Order

1. Add database fields with safe migrations.
2. Add backend service modules.
3. Add new API endpoints.
4. Route generation through `prompt_builder.py`.
5. Update frontend API client.
6. Update order detail UI for structured brief confirmation.
7. Update generation UI gating and trace display.
8. Run checks and fix regressions.

## Review Notes

This design is intentionally Phase 1 scoped. It builds the application spine that later quality feedback, analytics, and model training can attach to without forcing those larger systems into the first implementation pass.
