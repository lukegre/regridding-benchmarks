# Linux amd64 manifest for micromamba 2.3.3.
ARG MAMBA_IMAGE=docker.io/mambaorg/micromamba@sha256:e583f8e151fd1ebbc78b05cf4feb37ddbb518892dbabf6c0c03ea8ad613bc519
FROM ${MAMBA_IMAGE}
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/benchmark
COPY requirements-compiled.lock requirements-compiled-extras.lock requirements-python.lock ./
RUN micromamba create -y -p /opt/benchmark/compiled -f requirements-compiled.lock && \
    /opt/benchmark/compiled/bin/python -m pip install --no-cache-dir -r requirements-compiled-extras.lock && \
    /opt/benchmark/compiled/bin/python -m venv /opt/benchmark/.venv && \
    /opt/benchmark/.venv/bin/python -m pip install --no-cache-dir -r requirements-python.lock && \
    /opt/benchmark/.venv/bin/python -m pip install --no-cache-dir jupyterlab==4.4.10 && \
    micromamba clean --all --yes
COPY environments/requirements-workloads-linux-x86_64.lock ./
RUN /opt/benchmark/.venv/bin/python -m pip install --no-cache-dir --only-binary=:all: \
    --require-hashes -r requirements-workloads-linux-x86_64.lock
COPY environments/requirements-xhealpixify-linux-x86_64.lock ./
RUN /opt/benchmark/compiled/bin/python -m venv /opt/benchmark/xhealpixify && \
    /opt/benchmark/xhealpixify/bin/python -m pip install --no-cache-dir --only-binary=:all: \
    --require-hashes -r requirements-xhealpixify-linux-x86_64.lock && \
    /opt/benchmark/xhealpixify/bin/python -m pip install --no-cache-dir --no-deps --no-build-isolation \
    'xhealpixify @ git+https://github.com/IAOCEA/xhealpixify.git@8ebd09eb7db4ee4bc9b12f8dd05ccd436986a93c'
COPY . /opt/benchmark/source
RUN /opt/benchmark/.venv/bin/python -m pip install --no-cache-dir --no-deps /opt/benchmark/source && \
    mkdir -p /work /cache /results && chmod 1777 /work /cache /results
ENV BENCH_ENV_ROOT=/opt/benchmark BENCH_PYTHON=/opt/benchmark/.venv/bin/python \
    BENCH_XHEALPIXIFY_PYTHON=/opt/benchmark/xhealpixify/bin/python \
    BENCH_COMPILED_PYTHON=/opt/benchmark/compiled/bin/python PATH=/opt/benchmark/.venv/bin:/opt/benchmark/compiled/bin:$PATH \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 \
    NUMBA_CACHE_DIR=/work/numba MPLCONFIGDIR=/work/matplotlib HOME=/work
ARG BENCH_SOURCE_REV
LABEL org.opencontainers.image.revision=${BENCH_SOURCE_REV}
ENV BENCH_IMAGE_SOURCE_REV=${BENCH_SOURCE_REV}
USER 1000:100
WORKDIR /work
