# 🚀 Развертывание Atomic Hack через Dokploy

Dokploy - это self-hosted платформа для развертывания приложений (аналог Vercel/Netlify), которая упрощает деплой Docker-приложений на вашем сервере.

## 📋 Содержание

- [Требования к серверу](#требования-к-серверу)
- [Установка Dokploy](#установка-dokploy)
- [Подготовка проекта](#подготовка-проекта)
- [Развертывание через Dokploy](#развертывание-через-dokploy)
- [Настройка переменных окружения](#настройка-переменных-окружения)
- [Мониторинг и логи](#мониторинг-и-логи)
- [Обновление приложения](#обновление-приложения)

## 🖥️ Требования к серверу

### Минимальные требования:
- **CPU**: 4 ядра
- **RAM**: 8 GB
- **Диск**: 50 GB SSD
- **OS**: Ubuntu 22.04/24.04 LTS или Debian 12

### Рекомендуемые требования:
- **CPU**: 8 ядер
- **RAM**: 16 GB
- **Диск**: 100 GB SSD
- **OS**: Ubuntu 24.04 LTS

### Программное обеспечение:
- Docker 24.0+
- Docker Compose 2.0+
- Git

## 📦 Установка Dokploy

### 1. Подключитесь к серверу

```bash
ssh root@your-server-ip
```

### 2. Установите Dokploy

```bash
curl -sSL https://dokploy.com/install.sh | sh
```

Установщик автоматически:
- Установит Docker и Docker Compose (если не установлены)
- Развернет Dokploy и Traefik (reverse proxy)
- Настроит базовую конфигурацию

### 3. Откройте панель управления

После установки Dokploy будет доступен по адресу:
```
http://your-server-ip:3000
```

Первый вход создаст admin аккаунт.

### 4. (Опционально) Настройте HTTPS

В панели Dokploy перейдите в **Settings → Domain** и укажите ваш домен:
```
dokploy.yourdomain.com
```

Dokploy автоматически получит SSL сертификат через Let's Encrypt.

## 🔧 Подготовка проекта

### 1. Создайте репозиторий

Убедитесь что ваш проект находится в Git репозитории:

```bash
cd /path/to/atomic_hack
git init
git add .
git commit -m "Initial commit"
```

Загрузите в GitHub/GitLab:

```bash
git remote add origin https://github.com/yourusername/atomic_hack.git
git push -u origin main
```

### 2. Проверьте структуру проекта

Убедитесь что в корне проекта есть:
- ✅ `docker-compose.yml`
- ✅ `Dockerfile.backend`
- ✅ `Dockerfile.frontend`
- ✅ `nginx.conf`
- ✅ `.dockerignore`

## 🚢 Развертывание через Dokploy

### Шаг 1: Создайте новый проект

1. Войдите в панель Dokploy
2. Нажмите **Create Project**
3. Введите название: `atomic-hack`
4. Нажмите **Create**

### Шаг 2: Добавьте приложение

1. В проекте нажмите **Add Service**
2. Выберите **Docker Compose**
3. Укажите параметры:
   - **Name**: `atomic-hack-app`
   - **Repository URL**: `https://github.com/yourusername/atomic_hack.git`
   - **Branch**: `main`
   - **Compose File**: `docker-compose.yml`

### Шаг 3: Настройте переменные окружения

В разделе **Environment Variables** добавьте все переменные из `.env.example`:

#### Backend переменные:

```bash
# Database (используйте имя сервиса из docker-compose)
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/atomic_hack

# OpenAI API
OPENAI_API_BASE=https://foundation-models.api.cloud.ru/v1
OPENAI_API_KEY=your-actual-api-key-here
MODEL_NAME=Qwen/Qwen3-Next-80B-A3B-Instruct
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
LLM_TEMPERATURE=0.7

# Qdrant (используйте имя сервиса из docker-compose)
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

# Gotenberg (используйте имя сервиса из docker-compose)
GOTENBERG_URL=http://gotenberg:3030

# S3 Storage - MinIO (используйте имя сервиса из docker-compose)
TEMPLATE_BUCKET_NAME=atomic-hack-presentations
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_USE_SSL=false
S3_ADDRESSING_STYLE=path
AWS_REGION=us-east-1

# Или используйте внешний S3 (AWS, Yandex Object Storage, и т.д.):
# S3_ENDPOINT_URL=https://s3.amazonaws.com
# S3_ACCESS_KEY_ID=your-s3-key
# S3_SECRET_ACCESS_KEY=your-s3-secret
# S3_USE_SSL=true
# S3_ADDRESSING_STYLE=auto

# Kandinsky (опционально)
KANDINSKY_API_KEY=your-kandinsky-key
KANDINSKY_SECRET_KEY=your-kandinsky-secret

# OCR
ENABLE_OCR=true
MIN_TEXT_LENGTH=1000

# Vision Model (опционально)
QWEN_VL_API_BASE=https://bothub.chat/api/v2/openai/v1
QWEN_VL_API_KEY=your-qwen-api-key
QWEN_VL_MODEL_NAME=qwen2.5-vl-32b-instruct
```

#### Frontend переменные (Build Args):

**КРИТИЧЕСКИ ВАЖНО:** Frontend должен знать URL вашего backend API **ДО СБОРКИ**!

Vite встраивает переменные окружения в код при сборке. В Dokploy настройте **Build Arguments**:

```bash
# Для production (замените на ваш реальный домен backend)
VITE_API_URL=https://api.yourdomain.com
VITE_API_MODE=api
```

**Где настроить в Dokploy:**
1. Откройте настройки сервиса **frontend**
2. Перейдите в раздел **Build**
3. Добавьте **Build Arguments**:
   - Ключ: `VITE_API_URL`, Значение: `https://api.yourdomain.com`
   - Ключ: `VITE_API_MODE`, Значение: `api`
4. Пересоберите приложение

**⚠️ НЕ используйте** `http://localhost:8000` в production - это не будет работать!

**Пример для docker-compose локально:**
```bash
# Создайте файл .env в корне проекта
echo "VITE_API_URL=http://localhost:8000" > .env
echo "VITE_API_MODE=api" >> .env

# При сборке автоматически подхватится
docker-compose up --build
```

### Шаг 4: Настройте домены

1. Перейдите в **Domains**
2. Добавьте домены:
   - **Frontend**: `app.yourdomain.com` → порт `5173` (или `80`)
   - **Backend API**: `api.yourdomain.com` → порт `8000`

Dokploy автоматически:
- Настроит Traefik reverse proxy
- Получит SSL сертификаты через Let's Encrypt
- Настроит автоматическое обновление сертификатов

### Шаг 5: Деплой

1. Нажмите **Deploy**
2. Дождитесь завершения сборки (5-10 минут)
3. Проверьте логи во вкладке **Logs**

### Шаг 6: Настройка MinIO (S3 хранилище)

После развертывания нужно создать bucket в MinIO:

1. Откройте MinIO Console:
   ```
   http://your-server-ip:9001
   ```

2. Войдите с учетными данными:
   - **Username**: `minioadmin`
   - **Password**: `minioadmin`

3. Создайте bucket:
   - Нажмите **Buckets** → **Create Bucket**
   - **Bucket Name**: `atomic-hack-presentations`
   - Нажмите **Create**

4. Настройте доступ (опционально):
   - Выберите созданный bucket
   - **Access Policy** → **Public** (для публичного доступа к файлам)
   - Или настройте Access Keys для безопасного доступа

**Альтернатива:** Используйте внешний S3 (AWS, Yandex Object Storage) - укажите соответствующие credentials в переменных окружения.

### Шаг 7: Проверка

После успешного деплоя проверьте:

```bash
# Frontend
curl https://app.yourdomain.com

# Backend API
curl https://api.yourdomain.com/docs

# Здоровье приложения
curl https://api.yourdomain.com/api/health

# MinIO (должен быть доступен)
curl http://your-server-ip:9000/minio/health/live
```

## ⚙️ Расширенная конфигурация

### Масштабирование сервисов

В `docker-compose.yml` можно настроить replicas:

```yaml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Настройка персистентных данных

Dokploy автоматически создает volumes для:
- PostgreSQL данных
- Qdrant векторной БД
- Логов приложения

Volumes хранятся в: `/var/lib/dokploy/data/`

### Backup и восстановление

#### Создание backup:

```bash
# PostgreSQL
docker exec -t atomic_hack_postgres pg_dump -U postgres atomic_hack > backup.sql

# Qdrant
docker exec -t atomic_hack_qdrant tar -czf - /qdrant/storage > qdrant_backup.tar.gz
```

#### Восстановление:

```bash
# PostgreSQL
cat backup.sql | docker exec -i atomic_hack_postgres psql -U postgres atomic_hack

# Qdrant
docker exec -i atomic_hack_qdrant tar -xzf - -C /
```

## 📊 Мониторинг и логи

### Просмотр логов в Dokploy

1. Откройте проект в панели
2. Перейдите во вкладку **Logs**
3. Выберите сервис (backend/frontend/postgres/etc.)
4. Логи обновляются в реальном времени

### Просмотр логов через SSH

```bash
# Все сервисы
docker-compose -f /var/lib/dokploy/projects/atomic-hack/docker-compose.yml logs -f

# Конкретный сервис
docker-compose logs -f backend

# Последние 100 строк
docker-compose logs --tail=100 backend
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Статус всех сервисов
docker-compose ps
```

## 🔄 Обновление приложения

### Через Dokploy (рекомендуется)

1. Запушьте изменения в Git:
   ```bash
   git add .
   git commit -m "Update app"
   git push
   ```

2. В панели Dokploy нажмите **Redeploy**

Dokploy автоматически:
- Подтянет последние изменения
- Пересоберет образы
- Выполнит rolling update (zero downtime)

### Через SSH (ручное обновление)

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Перейдите в директорию проекта
cd /var/lib/dokploy/projects/atomic-hack

# Подтяните изменения
git pull

# Пересоберите и перезапустите
docker-compose up -d --build
```

## 🔐 Безопасность

### Рекомендации:

1. **Firewall**: Откройте только необходимые порты
   ```bash
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 3000/tcp  # Dokploy панель
   ufw enable
   ```

2. **SSH ключи**: Отключите вход по паролю
   ```bash
   # /etc/ssh/sshd_config
   PasswordAuthentication no
   ```

3. **Переменные окружения**: Храните секреты в Dokploy Secrets, а не в коде

4. **Регулярные обновления**:
   ```bash
   apt update && apt upgrade -y
   ```

5. **Backup**: Настройте автоматический backup БД (cron)

## 🐛 Troubleshooting

### Проблема: Контейнер не запускается

```bash
# Проверьте логи
docker-compose logs backend

# Проверьте конфигурацию
docker-compose config

# Пересоберите образы
docker-compose build --no-cache backend
```

### Проблема: База данных недоступна

```bash
# Проверьте статус PostgreSQL
docker-compose ps postgres

# Подключитесь к БД
docker exec -it atomic_hack_postgres psql -U postgres -d atomic_hack

# Проверьте логи
docker-compose logs postgres
```

### Проблема: Out of memory

```bash
# Проверьте использование памяти
docker stats

# Очистите неиспользуемые образы
docker system prune -a

# Увеличьте swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

### Проблема: SSL сертификат не получен

```bash
# Проверьте что домен указывает на ваш сервер
dig yourdomain.com

# Проверьте логи Traefik
docker logs traefik

# Попробуйте обновить сертификат вручную в Dokploy
```

## 📞 Поддержка

### Полезные ссылки:

- **Dokploy Documentation**: https://docs.dokploy.com
- **Dokploy GitHub**: https://github.com/Dokploy/dokploy
- **Community Forum**: https://github.com/Dokploy/dokploy/discussions

### Логирование проблем:

При возникновении проблем соберите:
1. Логи сервиса: `docker-compose logs service_name`
2. Вывод `docker ps`
3. Вывод `docker-compose config`
4. Переменные окружения (без секретов!)

## 🎯 Checklist развертывания

- [ ] Сервер соответствует требованиям
- [ ] Dokploy установлен и доступен
- [ ] Проект загружен в Git
- [ ] Все переменные окружения настроены
- [ ] Домены указывают на сервер
- [ ] SSL сертификаты получены
- [ ] Приложение успешно развернуто
- [ ] Backend API доступен
- [ ] Frontend загружается
- [ ] База данных работает
- [ ] Настроен backup
- [ ] Firewall настроен
- [ ] Мониторинг работает

---

**Готово!** 🎉 Ваш Atomic Hack развернут и работает на production сервере через Dokploy.
