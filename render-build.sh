#!/usr/bin/env bash
# Прерывать выполнение при ошибке
set -o errexit

# 1. Установка Python зависимостей
pip install -r requirements.txt

# 2. Скачивание ffmpeg (статичная сборка для Linux)
# Проверяем, нет ли уже скачанного в директории сборки
if [ ! -d "ffmpeg_bin" ]; then
  echo "Downloading ffmpeg..."
  mkdir -p ffmpeg_bin
  cd ffmpeg_bin
  wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
  tar xvf ffmpeg-release-amd64-static.tar.xz --strip-components=1
  rm ffmpeg-release-amd64-static.tar.xz
  cd ..
fi
