# Authentic Dynamics — free AI Labs

## What is now implemented
Each of the ten published research articles includes a working browser tool, and each tool has a dedicated route at \`/tools/ai-lab/<article-slug>\`.
The Blog and Free Tools catalogs link to these routes. These interactive utilities require no sign-in and make no paid model API calls.

| Article category | Working browser feature | Model not yet integrated |
| --- | --- | --- |
| Website | Input-validated HTML homepage preview, safe sandbox, HTML download | DeepSeek V4.1 Flash |
| Menu OCR | Photo preview, manual parsing, owner approval, HTML/JSON export | Unlimited-OCR |
| Voicemail | Local recording playback, optional browser dictation, reply and notes | NVIDIA Parakeet |
| Voiceover | Device text-to-speech, voice/rate selection, script download | Fish Audio Drama 3 |
| Image | Canvas-based branded graphics with photo and PNG export | Qwen Image 2.1 Turbo |
| Video | Locally rendered animated, silent WebM promotional video | LTX 2.5 |
| Document search | Local TXT/MD/CSV line/term search and evidence export | EmbeddingGemma 2 |
| Local AI fit | Quantization/memory illustration, brief export | Liquid LFM2.5 |
| Forecast | Chronological naïve/mean/seasonal baseline, MAE, CSV export | Timestral |
| Product cutout | Draw polygon mask and export original-pixel transparent PNG | Meta SAM 3 |

## Claims and privacy
The research models are NOT running in these public browser tools. The browser implements an immediately useful task rather than a simulated 'AI' result. Copy throughout the public UI makes that distinction. Visitors should not infer that the article's named model was installed, benchmarked, or connected. In particular, voice dictation may use the browser vendor's cloud service. No PythonAnywhere or GPU inference expenses are authorized or required for these utilities. No outbound SMS, POS write, purchase, autonomous agent, or other external action is enabled.

## Deployment
Pull the change and reload the PythonAnywhere app after tests. No new Python dependencies or database migration are required.

\`\`\`bash
git pull --ff-only origin main
python -m pytest -q tests/test_ai_lab.py tests/test_blog.py tests/test_blog_content.py tests/test_sitemap.py
python -m ruff check authentic_dynamics/blueprints/tools/routes.py
\`\`\`

Validate on desktop and mobile: navigation, all ten blog links, empty/invalid form handling, output/downloads, and browser feature failure states. Video creation needs MediaRecorder and canvas capture; voice playback depends on device support. Recorded content, photos, and documents are not uploaded by these tools. On the independent voice dictation feature, the browser vendor may process microphone audio.

## Deploying the named AI models later
Model-backed inference remains a separate technical project. Provision and monitor a controlled worker; confirm model-specific commercial licensing and gate requirements, then implement a reviewed input/output contract with queue limits, user consent, file validation, timeout and data-retention controls. Never put worker tokens in browser JavaScript or imply that these utilities already invoke the named models. Review especially Fish Audio, Qwen Image, Timestral, Liquid and SAM 3 terms before public model-serving.
