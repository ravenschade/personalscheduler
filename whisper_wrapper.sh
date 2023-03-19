#!/bin/bash

# Pyenv environment variables
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
# Pyenv initialization
if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init -)"
fi

pyenv local 3.10.10
d=`dirname "$1"`
whisper "$1" --model large --language German --output_format json --task transcribe --fp16 False --output_dir $d

