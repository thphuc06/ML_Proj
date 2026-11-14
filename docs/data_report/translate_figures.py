"""Translate vector chart labels without changing plotted data (requires PyMuPDF).

Run from any directory: python docs/data_report/translate_figures.py.
Proper names are retained; numbers keep their values and switch to English digit grouping (1.839 -> 1,839).
Text that overlaps a translated label is re-inserted unchanged, so no neighbouring label is lost.
Output: figures_en/*.pdf (English edition) and figures_vi/*.pdf (Vietnamese edition, where only code-style
group names such as train_extra / top_score are replaced by the report's terms).
"""
from pathlib import Path
import math
import re
import pymupdf as fitz

ROOT = Path(__file__).resolve().parent
TRANSLATIONS = {
    "Độ sáng (xám trung bình nửa trên pano)": "Brightness (upper-half panorama mean)",
    "Phân bố độ sáng và khoảng cách theo nhóm (hộp = Q1–Q3, râu = 1,5·IQR)": "Brightness and distance by group (box: Q1-Q3; whiskers: 1.5 IQR)",
    "Khoảng cách tới tim đường (m)": "Distance to street centreline (m)",
    "Main tự nhiên": "Natural main", "main tự nhiên": "natural main",
    "ngưỡng đêm 90": "night threshold 90", "Năm chụp": "Capture year",
    "Số ảnh cắt": "Crop count", "Năm chụp theo nhà đóng góp (creator) Mapillary": "Capture year by Mapillary creator",
    "Số ảnh theo nhãn trong từng nhóm (các nhóm không gộp)": "Label counts by group (groups kept separate)",
    "Còn lối đi": "Passable", "Bị chặn": "Blocked", "Không đủ thông tin": "Insufficient information",
    "Số ảnh dùng được (0 và 1) trong train": "Usable training images (0 and 1)",
    "(đủ, train hiện tại)": "(current training set)",
    "Thành phần train trước và sau khi thêm train-extra (83% ảnh Bị chặn của train đến từ train-extra)": "Training composition before/after enrichment (83% of positives from enrichment)",
    "Tỉ lệ nhãn trong đường (số ảnh ghi trong ô)": "Label share within street (counts inside bars)",
    "Bị chặn/dùng được": "Blocked/usable",
    "Thành phần nhãn của 17 đường main tự nhiên (không gồm 150 ảnh pilot)": "Label composition of 17 main streets (excluding 150 pilot images)",
    "Tỉ lệ ảnh Bị chặn có thẻ (nhiều thẻ/ảnh)": "Share of blocked images with tag (multiple tags allowed)",
    "Xe máy đậu": "Parked motorcycles", "Hàng hóa / quầy hàng": "Goods / stalls",
    "Bàn ghế quán": "Cafe furniture", "Ô tô đậu": "Parked cars",
    "Rào chắn / công trình": "Barriers / construction", "Khác": "Other",
    "Vật cản trên ảnh Bị chặn": "Obstacles in blocked images", "ảnh Bị chặn": "blocked images",
    "Tỉ lệ trong các ảnh I có ghi lý do": "Share of I images with a recorded reason",
    "Không thấy": "No visible", "vỉa hè": "sidewalk", "Bị che": "Occluded",
    "Ảnh mờ / tối /": "Blur / dark /", "cháy sáng": "overexposure",
    "Lý do khác": "Other reason", "Lý do Không đủ thông tin": "Reasons for insufficient information",
    "ảnh I có lý do": "I images with reason", "Main: mọi lượt gán (4.435 lượt)": "Main: all annotation records (4,435)",
    "Train-extra: nhãn v1 (2.000 lượt)": "Enrichment: v1 annotations (2,000)",
    "độ sáng": "brightness", "khoảng cách": "distance", "tới tim đường": "to centreline",
    "vĩ độ": "latitude", "kinh độ": "longitude", "năm chụp": "capture year",
    "hướng chạy xe": "travel heading", "điểm bộ chọn": "selector score",
    "(gộp 3 split, n=2.999)": "(3 splits pooled, n=2,999)",
    "Hệ số Spearman": "Spearman coefficient", "Tương quan hạng giữa các thuộc tính số của siêu dữ liệu": "Rank correlations among numeric metadata",
    "Độ tương đồng cosine (DINOv2)": "Cosine similarity (DINOv2)", "Mật độ": "Density",
    "Khoảng cách Hamming dHash (64 bit)": "dHash Hamming distance (64 bit)",
    "Ngưỡng cosine t": "Cosine threshold t", "Ngưỡng dHash t": "dHash threshold t",
    "Tỉ lệ cặp có cosine ≥ t": "Share of pairs with cosine >= t", "Tỉ lệ cặp có dHash ≤ t": "Share of pairs with dHash <= t",
    "Cùng vị trí, khác ngày": "Same position, different dates", "Cùng đường, khác vị trí": "Same street, different positions", "Khác đường": "Different streets",
    "Kinh độ (°E)": "Longitude (°E)", "Vĩ độ (°N)": "Latitude (°N)",
    "Mỗi chấm = một pano; tỉ lệ x:y theo mét": "One point per panorama; metric x:y aspect ratio",
    "Theo nhóm dữ liệu": "By data component", "Theo nhãn (chỉ để tô màu)": "By label (colouring only)",
    "0 thông được": "0 passable", "I thiếu thông tin": "I insufficient information", "1 bị chặn": "1 blocked",
    "Độ sáng trung bình (xám Rec.601, 0–255)": "Mean luminance (Rec.601 grey, 0-255)",
    "Độ nét (phương sai Laplacian, thang log)": "Sharpness (Laplacian variance, log scale)",
    "(a) Theo nhóm và nhãn (hộp: Q1–Q3, vạch: trung vị)": "(a) By group and label (box: Q1-Q3; line: median)",
    "(b) main tự nhiên (train+val+test), theo nhãn": "(b) Natural main (train+val+test), by label",
    # sampling components and strata: use the descriptive names of the report text
    "Train-extra – top_score": "Enrichment – top-score", "Train-extra – random": "Enrichment – random",
    "train_extra top_score": "enrichment top-score", "train_extra random": "enrichment random",
    "extra top_score": "top-score stratum", "extra random": "random stratum",
    "Train-extra": "Enrichment", "train-extra": "enrichment", "train_extra": "enrichment",
    " + extra": " + enrichment", "top_score": "top-score",
}

# Vietnamese edition: keep the Vietnamese charts, only replace code-style group names with report terms.
VI_NAMES = {
    "Main tự nhiên – ": "Bộ chính – ", "main tự nhiên": "bộ chính", "Main: ": "Bộ chính: ",
    "Train-extra – top_score": "Ảnh bổ sung – tầng điểm cao", "Train-extra – random": "Ảnh bổ sung – tầng ngẫu nhiên",
    "train_extra top_score": "ảnh bổ sung, tầng điểm cao", "train_extra random": "ảnh bổ sung, tầng ngẫu nhiên",
    "extra top_score": "tầng điểm cao", "extra random": "tầng ngẫu nhiên",
    "(top_score + random)": "(điểm cao + ngẫu nhiên)",
    "Train-extra": "Ảnh bổ sung", "train-extra": "ảnh bổ sung", "train_extra": "ảnh bổ sung", " + extra": " + ảnh bổ sung",
    "main (train)": "bộ chính (train)", "main train": "bộ chính train", "main val": "bộ chính val",
    "main test": "bộ chính test",
    "dùng được": "hợp lệ",
}

FONT_FILE = Path("C:/Windows/Fonts/arial.ttf")  # Helvetica-like, covers Vietnamese, en dash and degree sign
MIN_SCALE = 0.8  # a longer label may shrink to 80% of the original size, then it extends instead
GROUPED = re.compile(r"(?<![\d.,])([1-9]\d{0,2})((?:\.\d{3})+)(?![\d])")  # 1.839, 12.867.475 (not 0.005)


def translate(text, table=TRANSLATIONS, english_numbers=True):
    for source, target in sorted(table.items(), key=lambda x: -len(x[0])):
        text = text.replace(source, target)
    if english_numbers:
        text = GROUPED.sub(lambda m: m.group(1) + m.group(2).replace(".", ","), text)
    return text


def spans_of(page):
    return [(span, line["dir"]) for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", []) for span in line["spans"] if span["text"].strip()]


def alignment(span, others):
    """Guess matplotlib alignment of a horizontal label from labels that share an edge with it."""
    x0, _, x1, _ = span["bbox"]
    same = [o for o, d in others if o is not span and abs(d[1]) < 0.1]
    if any(abs(o["bbox"][2] - x1) < 0.6 and abs(o["bbox"][0] - x0) > 1 for o in same):
        return "right"
    if any(abs(o["bbox"][0] - x0) < 0.6 and abs(o["bbox"][2] - x1) > 1 for o in same):
        return "left"
    return "center"


def place(page, font, span, direction, text, others):
    """Insert text where the original span was, anchored like the original and at most slightly smaller."""
    rect, size = fitz.Rect(span["bbox"]), span["size"]
    cos, sin = direction
    if abs(sin) < 0.1:                      # horizontal
        old_len = rect.width
    elif abs(cos) < 0.1:                    # vertical axis label
        old_len = rect.height
    else:                                   # diagonal tick label
        old_len = max(rect.width - size * abs(sin), 1) / abs(cos)
    new_len = font.text_length(text, fontsize=size)
    if new_len > old_len:
        size = max(size * old_len / new_len, span["size"] * MIN_SCALE)
        new_len = font.text_length(text, fontsize=size)
    origin = fitz.Point(span["origin"])
    if abs(sin) < 0.1:
        how = alignment(span, others)
        shift = {"left": 0, "center": (old_len - new_len) / 2, "right": old_len - new_len}[how]
    elif abs(cos) < 0.1:
        shift = (old_len - new_len) / 2      # axis titles are centred
    else:
        shift = old_len - new_len            # rotated tick labels end at the axis
    origin = origin + fitz.Point(cos, sin) * shift
    angle = -math.degrees(math.atan2(sin, cos))
    page.insert_text(origin, text, fontname="F0", fontsize=size, color=fitz.sRGB_to_pdf(span["color"]),
                     morph=(origin, fitz.Matrix(angle)))


def figure_names(lang):
    if lang == "en":
        text = (ROOT / "sections_en/report.tex").read_text(encoding="utf-8")
        return re.findall(r"\\plot\{([^}]+\.pdf)\}", text)
    text = "".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "sections").glob("*.tex")))
    return sorted(set(re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+\.pdf)\}", text)))


def main():
    font = fitz.Font(fontfile=str(FONT_FILE)) if FONT_FILE.exists() else fitz.Font("helv")
    for lang, table, english_numbers in [("en", TRANSLATIONS, True), ("vi", VI_NAMES, False)]:
        output = ROOT / f"figures_{lang}"
        output.mkdir(exist_ok=True)
        for name in figure_names(lang):
            relabel(ROOT / "figures" / name, output / name, font, table, english_numbers)
            print(f"figures_{lang}/{name}")


def relabel(source, target, font, table, english_numbers):
    doc = fitz.open(source)
    for page in doc:
        spans = spans_of(page)
        new = {id(s): translate(s["text"], table, english_numbers) for s, _ in spans}
        redo = {id(s): (s, d, new[id(s)]) for s, d in spans if new[id(s)] != s["text"]}
        if redo:
            # Redaction removes every character inside the rectangle, so a neighbouring label that overlaps a
            # translated one would be cut. Re-insert such labels unchanged (repeat until no new overlaps).
            while True:
                rects = [fitz.Rect(s["bbox"]) for s, _, _ in redo.values()]
                hit = [(s, d) for s, d in spans if id(s) not in redo
                       and any((fitz.Rect(s["bbox"]) & r).get_area() > 0 for r in rects)]
                if not hit:
                    break
                redo.update({id(s): (s, d, s["text"]) for s, d in hit})
            for s, _, _ in redo.values():
                page.add_redact_annot(s["bbox"], fill=False)
            page.apply_redactions(images=0, graphics=0)  # text only; chart paths, points and images stay
            page.insert_font(fontname="F0", fontbuffer=font.buffer)
            for s, d, text in redo.values():
                place(page, font, s, d, text, spans)
    doc.save(target, garbage=4, deflate=True)


if __name__ == "__main__":
    main()
