# Ingestion Adapters
Pipeline: scanner -> classifier -> registry -> adapter -> normalized records -> storage.
Adapters: filesystem, text, changelog, docx, pdf, image, diagram_json, pptx, unknown_file.
Unknown/unsupported files are still registered as artifacts.
