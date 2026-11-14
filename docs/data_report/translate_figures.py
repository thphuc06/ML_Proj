"""Translate vector chart labels without changing plotted data (requires PyMuPDF).

Run from any directory: python docs/data_report/translate_figures.py.
Proper names and numeric annotations are retained. Output is figures_en/*.pdf.
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
    "(đủ, train hiện tại)": "(full current training set)",
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
    "Kinh độ (°E)": "Longitude (degrees E)", "Vĩ độ (°N)": "Latitude (degrees N)",
    "Mỗi chấm = một pano; tỉ lệ x:y theo mét": "One point per panorama; metric x:y aspect ratio",
    "Theo nhóm dữ liệu": "By data component", "Theo nhãn (chỉ để tô màu)": "By label (colouring only)",
    "0 thông được": "0 passable", "I thiếu thông tin": "I insufficient information", "1 bị chặn": "1 blocked",
    "Độ sáng trung bình (xám Rec.601, 0–255)": "Mean luminance (Rec.601 grey, 0-255)",
    "Độ nét (phương sai Laplacian, thang log)": "Sharpness (Laplacian variance, log scale)",
    "(a) Theo nhóm và nhãn (hộp: Q1–Q3, vạch: trung vị)": "(a) By group and label (box: Q1-Q3; line: median)",
    "(b) main tự nhiên (train+val+test), theo nhãn": "(b) Natural main (train+val+test), by label",
}


def translate(text):
    for source, target in sorted(TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        text = text.replace(source, target)
    return text


def main():
    output = ROOT / "figures_en"
    output.mkdir(exist_ok=True)
    names = re.findall(r"\\plot\{([^}]+\.pdf)\}", (ROOT / "sections_en/report.tex").read_text(encoding="utf-8"))
    for name in names:
        doc = fitz.open(ROOT / "figures" / name)
        for page in doc:
            edits = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        original = span["text"]
                        translated = translate(original)
                        if translated == original:
                            continue
                        edits.append((span, line["dir"], translated))
                        page.add_redact_annot(span["bbox"], fill=False)
            # Remove only text; keep chart paths, points and images intact.
            page.apply_redactions(images=0, graphics=0)
            for span, direction, text in edits:
                origin = fitz.Point(span["origin"])
                rect = fitz.Rect(span["bbox"])
                old_length = rect.height if abs(direction[1]) > 0.7 else rect.width
                size = min(span["size"], old_length / max(fitz.get_text_length(text, fontname="helv", fontsize=1), 1))
                rgb = fitz.sRGB_to_pdf(span["color"])
                angle = -math.degrees(math.atan2(direction[1], direction[0]))
                page.insert_text(origin, text, fontname="helv", fontsize=size, color=rgb,
                                 morph=(origin, fitz.Matrix(angle)))
        doc.save(output / name, garbage=4, deflate=True)
        print(name)


if __name__ == "__main__":
    main()
