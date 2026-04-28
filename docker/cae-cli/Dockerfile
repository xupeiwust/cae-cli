FROM unifem/calculix-desktop:latest

LABEL org.opencontainers.image.title="cae-cli CalculiX runtime"
LABEL org.opencontainers.image.description="Local cae-cli runtime wrapper for the UNIFEM CalculiX image."

RUN test -x /tmp/calculix/ccx_2.13_MT \
    && ln -sf /tmp/calculix/ccx_2.13_MT /usr/local/bin/ccx

WORKDIR /work
ENTRYPOINT []
CMD ["bash", "-lc", "/tmp/calculix/ccx_2.13_MT -v || true"]
