"""Утилиты для красивого форматирования traceback."""

import traceback


class TracebackFormatter:
    """Форматировщик traceback с красивым выводом."""

    @staticmethod
    def format_traceback(exc: Exception) -> str:
        """
        Форматирует traceback с отступами и эмодзи.

        Returns:
            Отформатированный traceback
        """
        # Используем переданное исключение для форматирования
        tb_lines = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip().split("\n")
        formatted_lines = []

        for line in tb_lines:
            stripped_line = line.strip()

            if stripped_line.startswith("Traceback"):
                formatted_lines.append(f"🔍 {stripped_line}")
            elif stripped_line.startswith("File"):
                # Извлекаем имя файла и номер строки
                formatted_lines.append(f"  📁 {stripped_line}")
            elif stripped_line and "," in stripped_line and "line" in stripped_line:
                # Строка с кодом
                formatted_lines.append(f"    💻 {stripped_line}")
            elif stripped_line and not line.startswith(" "):
                # Сообщение об ошибке
                formatted_lines.append(f"❌ {stripped_line}")
            elif stripped_line:
                # Код с отступами
                formatted_lines.append(f"    ➤ {stripped_line}")
            else:
                # Пустая строка
                formatted_lines.append("")

        return "\n".join(formatted_lines)

    @staticmethod
    def format_traceback_json(exc: Exception) -> dict:
        """
        Форматирует traceback в структурированном виде для JSON.

        Args:
            exc: Исключение для форматирования

        Returns:
            Словарь с детализированной информацией об ошибке
        """
        tb = traceback.extract_tb(exc.__traceback__)

        frames = []
        for frame in tb:
            frames.append(
                {
                    "file": frame.filename,
                    "line": frame.lineno,
                    "function": frame.name,
                    "code": frame.line.strip() if frame.line else None,
                }
            )

        return {
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "frames": frames,
            "formatted": TracebackFormatter.format_traceback(exc),
        }
