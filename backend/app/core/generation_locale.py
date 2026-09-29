from typing import Literal


GenerationLocale = Literal["zh-CN", "id"]


def output_language_instruction(locale: GenerationLocale = "zh-CN") -> str:
    if locale == "id":
        return (
            "Bahasa keluaran wajib bahasa Indonesia. Tulis semua deskripsi, judul, prompt gambar, "
            "prompt video, dialog, narasi, dan teks layar yang dihasilkan dalam bahasa Indonesia alami. "
            "Aturan bahasa ini mengesampingkan bahasa contoh, materi referensi, dan template lama. "
            "Jangan menyalin teks contoh berbahasa Mandarin ke hasil. Gunakan label Adegan 1 sampai "
            "Adegan 6 untuk storyboard enam adegan, Gambar N untuk referensi gambar, dan Tokoh N "
            "untuk tokoh. Dialog harus diucapkan dalam bahasa Indonesia dengan pengucapan alami "
            "dan sinkronisasi bibir. Jangan menerjemahkan key JSON, ID, enum, nama merek, kode produk, "
            "URL, atau token referensi mesin. Pertahankan fakta dan maksud masukan pengguna. "
            "Jangan menambahkan dialog atau teks layar jika aturan tugas melarangnya."
        )
    return (
        "输出语言为简体中文：新生成的描述、标题、图片提示词、视频提示词、对白和旁白使用中文。"
        "JSON字段名、ID、枚举值、品牌名、产品代码、URL和机器引用标记保持不变。保留用户输入的事实与意图。"
    )
