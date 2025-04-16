#!/bin/bash
# Тестовый запрос к gptunnel.ru для проверки работы API-ключа
set -e

# Получаем API_KEY из .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY не найден в .env!" >&2
  exit 1
fi

curl --request POST \
  --url https://gptunnel.ru/v1/chat/completions \
  --header "Authorization: Bearer $OPENAI_API_KEY" \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "system", "content": "My name is Pupok."},
      {"role": "user", "content": "как тебя зовут"}
    ]
}'
