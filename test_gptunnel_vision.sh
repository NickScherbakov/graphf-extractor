#!/bin/bash
# Тест vision-запроса к gptunnel.ru (OpenAI API совместимость)
set -e

# Установка таймаута для curl
CURL_TIMEOUT=90

echo "🚀 Запускаем тест OpenAI Vision API через gptunnel.ru..."

# Получаем API_KEY из .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY не найден в .env!" >&2
  exit 1
fi

IMG_PATH="testimages/testimage.png"
if [ ! -f "$IMG_PATH" ]; then
  echo "Файл $IMG_PATH не найден!" >&2
  exit 1
fi

echo "🖼️ Подготовка изображения ($IMG_PATH)..."
echo "⚙️ Размер изображения: $(du -h "$IMG_PATH" | cut -f1)"

# Преобразуем изображение в base64 без вывода в терминал
echo "⏳ Кодирование изображения в base64..."
IMG_B64=$(base64 -w 0 "$IMG_PATH")
echo "✓ Кодирование завершено"

echo "📝 Формирование запроса к API..."
read -r -d '' DATA <<EOF
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "Ты — эксперт по анализу графов."},
    {"role": "user", "content": [
      {"type": "text", "text": "Определи список вершин и рёбер графа на изображении. Ответ только в формате Python: nodes = [...]; edges = [...]. Без пояснений."},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,$IMG_B64"}}
    ]}
  ],
  "max_tokens": 512
}
EOF

echo "📋 Запрос содержит изображение размером $(wc -c < "$IMG_PATH") байт"

echo -n "📤 Отправка запроса к gptunnel.ru [$(date +"%H:%M:%S")]... "

# Проверка наличия утилиты jq
if ! command -v jq &> /dev/null; then
    echo "⚠️ Утилита jq не установлена. Вывод будет в формате JSON."
    HAS_JQ=false
else
    HAS_JQ=true
fi

# Сохраняем время начала запроса
START_TIME=$(date +%s)

# Выполняем запрос с выводом прогресса
RESPONSE=$(curl --silent \
  --write-out "\n⏱️ Время запроса: %{time_total} сек, HTTP-код: %{http_code}" \
  --request POST \
  --url https://gptunnel.ru/v1/chat/completions \
  --header "Authorization: Bearer $OPENAI_API_KEY" \
  --header 'Content-Type: application/json' \
  --max-time $CURL_TIMEOUT \
  --data "$DATA")

# Вычисляем время выполнения
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Проверяем успешность запроса
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP-код: [0-9]*" | cut -d' ' -f2)
echo "✅ Запрос завершен [$(date +"%H:%M:%S")], общее время: ${DURATION} сек"

echo "📥 Получен ответ от API:"
if [[ "$HAS_JQ" == true ]]; then
    # Извлекаем только полезную часть ответа с помощью jq
    CONTENT=$(echo "$RESPONSE" | head -n 1 | jq -r '.choices[0].message.content' 2>/dev/null)
    if [[ $? -eq 0 && -n "$CONTENT" ]]; then
        echo "$CONTENT"
    else
        echo "⚠️ Не удалось обработать ответ. Возможно, формат ответа отличается от ожидаемого:"
        echo "$RESPONSE" | head -n 1
    fi
else
    # Если jq не установлен, выводим весь JSON-ответ
    echo "$RESPONSE" | head -n 1
fi
