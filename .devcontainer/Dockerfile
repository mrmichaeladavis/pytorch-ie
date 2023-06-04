FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ARG USERNAME
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN if [[ -z "$devcontainercli" ]] ; then printf "\nERROR: This Dockerfile needs to be built with VS Code !" && exit 1; else printf "VS Code is detected: $devcontainercli"; fi

USER root

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.5.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME=/app/poetry \
    POETRY_CACHE_DIR=/app/.cache \
    POETRY_VENV=/app/poetry-venv \
    PYSETUP_PATH="/app" \
    VIRTUAL_ENV="/app/venv"

RUN \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get -y install software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && \
    apt-get -y upgrade && apt-get -y install python3.10 \
    && apt-get -y install python3.10-venv git curl wget python3.10-dev \
    build-essential vim file git-annex ffmpeg sudo keychain unzip jq gh \
    pinentry-gtk2 ca-certificates tzdata bash-completion locales

RUN mkdir /app && chown $USER_UID:$USER_GID /app

# Source to use it
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME && \
    chown $USERNAME $(eval echo ~$USERNAME) && \
    chmod 755 $(eval echo ~$USERNAME)

# update CUDA Linux GPG repository key
RUN curl https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb && dpkg -i cuda-keyring_1.0-1_all.deb && rm cuda-keyring_1.0-1_all.deb
# clean up
RUN apt-get autoremove -y && apt-get clean

USER $USERNAME

# This prevents vscode from mounting GPG keys and forces dotfiles to deploy them.
# RUN mkdir -p ~/.gnupg/private-keys-v1.d && echo "pinentry-mode loopback" >> ~/.gnupg/gpg.conf

### Bootstrap

RUN python3.10 -m venv $VIRTUAL_ENV
# This is so we dont have to activate the venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip python -m ensurepip --upgrade

RUN --mount=type=cache,target=/root/.cache/pip pip install "poetry==$POETRY_VERSION"

RUN --mount=type=cache,target=/root/.cache/pip poetry config installer.max-workers 10

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

### Ready for use
