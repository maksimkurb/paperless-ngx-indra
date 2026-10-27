# Paperless-ngx with the Indra OCR engine plugin for OCRmyPDF.
ARG PAPERLESS_VERSION=latest
FROM ghcr.io/paperless-ngx/paperless-ngx:${PAPERLESS_VERSION}

ARG BAKE_MODELS=0
ARG PLUGIN_VERSION=dev

# Paperless installs its dependencies into the system Python with `uv pip install --system`
# and ships uv in the image, so the plugin goes into the same environment.
COPY pyproject.toml README.md LICENSE /tmp/plugin/
COPY src /tmp/plugin/src
RUN set -eux \
    && uv pip install --system --no-cache --no-python-downloads --python-preference system \
        /tmp/plugin \
    && rm -rf /tmp/plugin

# Model weights are under a modified OpenRAIL-M licence, so by default they are
# downloaded on first use into a volume rather than baked into the (public) image.
ENV INDRA_OCR_MODEL_DIR=/usr/src/paperless/indra-models \
    HF_HOME=/usr/src/paperless/indra-models/.hf \
    PAPERLESS_OCR_USER_ARGS='{"plugins": ["ocrmypdf_indra"]}'
RUN set -eux \
    && mkdir -p "${INDRA_OCR_MODEL_DIR}" \
    && if [ "${BAKE_MODELS}" = "1" ]; then \
         python3 -c "import indra_ocr; indra_ocr.model_dir(None)"; \
       fi \
    && chown -R paperless:paperless "${INDRA_OCR_MODEL_DIR}"
VOLUME ["/usr/src/paperless/indra-models"]

LABEL org.opencontainers.image.title="paperless-ngx-indra" \
      org.opencontainers.image.source="https://github.com/maksimkurb/paperless-ngx-indra" \
      org.opencontainers.image.version="${PLUGIN_VERSION}" \
      org.opencontainers.image.base.name="ghcr.io/paperless-ngx/paperless-ngx:${PAPERLESS_VERSION}"
