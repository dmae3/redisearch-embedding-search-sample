FROM python:3.11-slim

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# poetryをインストール
RUN curl -sSL https://install.python-poetry.org | python3 -

# PATHを通す
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# プロジェクトの依存関係を記述したファイルをコピー
COPY pyproject.toml ./

# Poetry の設定（仮想環境を作成しない）
RUN poetry config virtualenvs.create false

# 依存関係をインストール
RUN poetry install --no-interaction --no-ansi --no-root
