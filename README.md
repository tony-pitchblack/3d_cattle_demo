# 3d_cattle_demo

## Обзор репозитория
В этом репозитории собраны все ассеты, скрипты и данные, необходимые для генерации синтетических датасетов коров в Blender и их последующей обработки для задач машинного обучения.

| Путь | Тип | Назначение |
|------|-----|------------|
| `.git/`, `.gitignore`, `.gitmodules`, `.gitattributes` | meta | Служебные файлы Git. |
| `environment.yml` | файл | Спецификация Conda/Micromamba окружения. |
| `read_depth.ipynb` | ноутбук | Демонстрация чтения/визуализации карт глубины. |
| `blender_scripts/` | каталог | Python-скрипты для Blender (например, рендер глубины). |
| `manage_data/` | каталог | Bash-скрипты для загрузки/выгрузки данных на HuggingFace Hub. |
| `data/` | каталог | Исходники, сцены Blender и сгенерированные рендеры. Подробности ниже. |

---

## Структура `data/`
```
data/
├── baseline.blend*                # Основная сцена Blender (+ вспомогательный *.blend1)
├── configs/                       # YAML-пресеты фильтрации кадров symlink_filtered_images.sh
├── deeplabcut_results/            # Результаты инференса DeepLabCut
├── prod/                          # Продакшн-датасеты
├── renders/                       # Сырые рендеры из Blender
├── renders_filtered/              # Рендеры после фильтрации YAML-пресетами
├── renders_video_only/            # Только видео
├── source/                        # Исходные 3D-ассеты
└── tmp/                           # Временные файлы
```
Ключевые подпапки:

* **renders/** — организация по сценам ( `cow_boxed/`, `construction/` ) и сеттингам сцен (`sliding_clip_*`, `static_pose_*` и др.).
* **renders_filtered/** зеркалирует `renders/`, но содержит только отфильтрованные кадры.
* **renders_video_only/** хранит видео.
* **source/** — исходные ассеты: `cow/`, `construction/`, `camera_calibration/`.
* **configs/** — группы YAML, например `sliding_clip_120s_v2.1/filter_config.yml`, описывающие, какие кадры оставить.

### Сеттинги съёмки в `renders/`

| Пресет | Что генерирует | Особенности |
|--------|----------------|-------------|
| `sliding_clip_120s_v1`/`v2`/`v2.1`/`v3` | 120-секундный «проезд» камеры по дуге вокруг объекта | Версия задаёт траекторию, скорость и плотность кадров |
| `sliding_clip_120s_v2.1_600x300` | То же, но низкое разрешение 600×300 | Быстрые тесты |
| `static_pose_frame=<N>` | Один статичный кадр выбранного ключевого кадра | Удобно для отладки материалов и освещения |
| `depth_front_left` | Depth-pass из фронтально-левой камеры | Статичная камера, только глубина |
| `camera_calibration` | Снимки шахматной доски/маркеров | Используется для калибровки параметров камеры |
| `front_view` (сцена `construction`) | Фронтальный статичный ракурс стройплощадки | Несколько тайм-штампов |

Внутри каждого пресета могут быть подпапки:
* `case=<variant>` — вариант сцены (освещение, позиция объектов и др.), по умолчанию `default`;
* `render=<pass>` — тип пасса Blender (`rgb`, `depth`, `normal`, `segm` и т.п.).

---

## Пайплайн симлинков и фильтрации данных
1. Перейдите в каталог данных
   ```bash
   cd data/
   ```
2. Создайте симлинки на отфильтрованные изображения
   ```bash
   ./symlink_filtered_images.sh \
     --dir renders/cow_boxed/sliding_clip_120s_v2/case=default/render=depth
   ```
3. Разрешите симлинки (скопируйте файлы)
   ```bash
   ./resolve_symlinked.sh \
     --in renders_filtered/sliding_clip_120s_v2.1/case=default/render=depth \
     --flatten-last-dir
   ```
4. (Опционально) скопируйте временные данные в production-датасет
   ```bash
   mkdir -p prod/data_generation_source_v2
   cp <your_files_here> prod/data_generation_source_v2/
   ```

---

## Удалённый GPU-рендеринг через Flamenco
1. Установите Flamenco на рендер-сервер (смотри официальную документацию).
2. Настройте общую папку, куда сервер будет писать результаты, а клиент — читать.
3. Дайте пользователю сервера права на запись в репозиторий на клиенте:
   ```bash
   sudo chown bonting:bonting /home/bonting/3d_cattle_demo
   ```

---

## Монтирование репозитория через SSHFS
Примонтировать удаленный репо локально:
```bash
sudo mkdir -p /home/anton/3d_cattle_demo
sudo chown anton:anton /home/anton/3d_cattle_demo
sshfs \
  bonting@10.0.0.1:/home/bonting/3d_cattle_demo \
  /home/anton/3d_cattle_demo \
  -o reconnect \
  -o ServerAliveInterval=15 \
  -o allow_other
```
Отмонтировать:
```bash
sudo umount /home/anton/3d_cattle_demo
```

---

## FAQ
### Не удаётся запушить в репозиторий HF
Убедитесь, что все крупные файлы отслеживаются через Git-LFS:
```bash
git lfs migrate import --include="*.FBX,*.obj,*.stl,*.exr,*.STEP,*.blend,*.blend1,*.fspy"
```
### Не открывается Flamenco UI в браузере
Делаем следующий хак:
1. Через консоль VSCode открываем инфу по активному воркер сервису
```bash
sudo systemctl status flamenco-worker.service
```
2. Кликаем адрес localhost://8080 или что там отобразится

**TODO: пофиксить это - выполнять форвардинг портов без VSCode**
---

## Прочее
### Blender MCP
Плагин Blender MCP для Cursor: <https://github.com/ahujasid/blender-mcp>
