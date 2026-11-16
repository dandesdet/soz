#!/bin/sh
# Offline speech models (Vosk, Apache 2.0) repacked as .tar.gz for the browser (vosk-browser). Run by .github/workflows/models.yml.
set -e
mkdir -p models
for m in vosk-model-small-uz-0.22 vosk-model-small-es-0.42 vosk-model-small-en-us-0.15; do
  [ -f models/$m.tar.gz ] && continue
  curl -sfLO https://alphacephei.com/vosk/models/$m.zip && unzip -q $m.zip && tar czf models/$m.tar.gz $m && rm -rf $m $m.zip
done
ls -la models
