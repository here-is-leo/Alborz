import asyncio
import datetime
import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from Alborz.core.extractor import extract_metadata
from Alborz.core.formatters import dedup_entries, humanize_value
from Alborz.core.editor import compute_privacy_score, strip_metadata
from Alborz.core.geo import extract_gps_from_entries, reverse_geocode
from Alborz.core.report import generate_pdf_report
from Alborz.core.writer import edit_image_metadata, delete_tags
from Alborz.core.compare import compare_results
from Alborz.core.taginfo import get_tag_info

app = FastAPI(title="Alborz API", version="1.0.0")

BASE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=BASE / "web" / "templates")

static_dir = BASE / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

MAX_FILE_SIZE = 200 * 1024 * 1024


def safe_json(data) -> Response:
    """تبدیل امن به JSON حتی با انواع غیرسریال‌پذیر"""
    return Response(
        content=json.dumps(data, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Alborz"}


@app.get("/api/version")
async def api_version():
    """اطلاعات نسخه"""
    try:
        from Alborz import __version__, __description__, __author__
    except ImportError:
        __version__ = "1.0.0"
        __description__ = "Alborz"
        __author__ = "Alborz"
    return safe_json({
        "version": __version__,
        "description": __description__,
        "author": __author__,
    })


@app.get("/api/tag/{tag_name}")
async def api_tag_info(tag_name: str):
    """اطلاعات یک تگ"""
    return safe_json(get_tag_info(tag_name))


@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "نام فایل نامعتبر است")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            f"حجم فایل بیش از حد مجاز است (بیش از {MAX_FILE_SIZE // 1024 // 1024}MB)",
        )

    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = extract_metadata(tmp_path)
        result.filename = file.filename

        deduped = dedup_entries(result.entries)
        data = result.to_dict()
        data["entries"] = [
            {
                "group": e.group,
                "tag": e.tag,
                "value": str(humanize_value(e.tag, e.value)),
                "description": e.description,
            }
            for e in deduped
        ]
        data["summary"] = _build_summary(deduped)
        data["privacy"] = compute_privacy_score(deduped)
        return safe_json(data)

    except Exception as e:
        raise HTTPException(500, f"خطا در پردازش: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------- خلاصه هوشمند ----------
SUMMARY_TAGS = {
    "مدل دستگاه":     ["Model"],
    "سازنده":         ["Make"],
    "نرم‌افزار":       ["Software"],
    "لنز":            ["LensModel", "Lens"],
    "ساعت ضبط":       ["DateTimeOriginal", "DateTimeDigitized", "DateTime"],
    "آخرین تغییر":    ["DateTime"],
    "ISO":            ["ISOSpeedRatings", "PhotographicSensitivity"],
    "دیافراگم":       ["FNumber", "ApertureValue"],
    "سرعت شاتر":      ["ExposureTime", "ShutterSpeedValue"],
    "فاصله کانونی":   ["FocalLength"],
    "فلاش":           ["Flash"],
    "حالت نوردهی":    ["ExposureProgram", "ExposureMode"],
    "رزولوشن":        ["ExifImageWidth", "ImageWidth",
                       "ExifImageHeight", "ImageHeight"],
    "طول جغرافیایی":  ["DecimalLongitude"],
    "عرض جغرافیایی":  ["DecimalLatitude"],
    "ارتفاع":         ["GPSAltitude"],
}


def _build_summary(entries):
    rows = []
    for label, tags in SUMMARY_TAGS.items():
        for tag in tags:
            found = next((e for e in entries if e.tag.lower() == tag.lower()), None)
            if found and str(found.value).strip() not in ("", "None"):
                v = str(humanize_value(tag, found.value)).strip()
                if len(v) > 80:
                    v = v[:77] + "..."
                rows.append({"label": label, "value": v})
                break
    return rows


# ---------- امتیاز حریم خصوصی (endpoint مستقل) ----------
@app.post("/api/privacy-score")
async def api_privacy_score(file: UploadFile = File(...)):
    """محاسبه امتیاز حریم خصوصی"""
    contents = await file.read()
    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = extract_metadata(tmp_path)
        result.filename = file.filename
        deduped = dedup_entries(result.entries)
        score = compute_privacy_score(deduped)
        return safe_json(score)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------- حذف متادیتا ----------
@app.post("/api/strip")
async def api_strip(
    file: UploadFile = File(...),
    keep: str = Form(""),
):
    """حذف متادیتا و برگرداندن فایل پاک‌شده"""
    contents = await file.read()
    suffix = Path(file.filename).suffix or ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    out_path = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix,
        prefix=f"clean_{Path(file.filename).stem}_"
    ).name

    try:
        keep_groups = None
        if keep.strip():
            keep_groups = {g.strip().upper() for g in keep.split(",")}

        strip_metadata(tmp_path, out_path, keep_groups)

        clean_name = f"clean_{file.filename}"
        return FileResponse(
            out_path,
            media_type="application/octet-stream",
            filename=clean_name,
            background=None,
        )
    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)
        raise HTTPException(500, f"خطا در پاکسازی: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------- Batch Processing ----------

@app.post("/api/batch/extract")
async def api_batch_extract(files: List[UploadFile] = File(...)):
    """پردازش چند فایل همزمان"""
    if not files:
        raise HTTPException(400, "هیچ فایلی ارسال نشد")

    async def process_one(upload: UploadFile):
        try:
            contents = await upload.read()
            if len(contents) > MAX_FILE_SIZE:
                return {
                    "filename": upload.filename,
                    "error": f"حجم فایل بیش از حد مجاز ({MAX_FILE_SIZE // 1024 // 1024}MB)",
                }

            suffix = Path(upload.filename).suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(contents)
                tmp_path = tmp.name

            try:
                result = await asyncio.to_thread(extract_metadata, tmp_path)
                result.filename = upload.filename
                deduped = dedup_entries(result.entries)

                data = result.to_dict()
                data["entries"] = [
                    {
                        "group": e.group,
                        "tag": e.tag,
                        "value": str(humanize_value(e.tag, e.value)),
                        "description": e.description,
                    }
                    for e in deduped
                ]
                data["summary"] = _build_summary(deduped)
                data["privacy"] = compute_privacy_score(deduped)
                return data
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            return {"filename": upload.filename, "error": str(e)}

    results = await asyncio.gather(*[process_one(f) for f in files])
    return safe_json({"files": list(results), "count": len(results)})


@app.post("/api/batch/strip")
async def api_batch_strip(
    files: List[UploadFile] = File(...),
    keep: str = Form(""),
    mode: str = Form("full"),  # full | keep_exif | keep_all_but_gps
):
    """Strip دسته‌ای و برگرداندن ZIP"""
    if not files:
        raise HTTPException(400, "هیچ فایلی ارسال نشد")

    keep_groups = None
    if mode == "keep_exif":
        keep_groups = {"EXIF"}
    elif mode == "keep_all_but_gps":
        keep_groups = {"EXIF", "ExifIFD", "MakerNote"}
    elif keep.strip():
        keep_groups = {g.strip().upper() for g in keep.split(",")}

    zip_buffer = io.BytesIO()
    errors = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for upload in files:
            try:
                contents = await upload.read()
                suffix = Path(upload.filename).suffix or ".bin"

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(contents)
                    tmp_path = tmp.name

                out_path = tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix,
                    prefix=f"clean_{Path(upload.filename).stem}_"
                ).name

                try:
                    await asyncio.to_thread(
                        strip_metadata, tmp_path, out_path, keep_groups
                    )

                    with open(out_path, "rb") as f:
                        zf.writestr(f"clean_{upload.filename}", f.read())
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
                    Path(out_path).unlink(missing_ok=True)
            except Exception as e:
                errors.append(f"{upload.filename}: {e}")

    zip_buffer.seek(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"Alborz_cleaned_{ts}.zip"

    headers = {"Content-Disposition": f'attachment; filename="{zip_name}"'}
    if errors:
        headers["X-Errors"] = "; ".join(errors[:5])

    return Response(
        content=zip_buffer.read(),
        media_type="application/zip",
        headers=headers,
    )


@app.post("/api/batch/score")
async def api_batch_score(files: List[UploadFile] = File(...)):
    """امتیاز حریم خصوصی برای چند فایل"""
    async def score_one(upload: UploadFile):
        try:
            contents = await upload.read()
            suffix = Path(upload.filename).suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            try:
                result = await asyncio.to_thread(extract_metadata, tmp_path)
                deduped = dedup_entries(result.entries)
                score = compute_privacy_score(deduped)
                score["filename"] = upload.filename
                return score
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            return {"filename": upload.filename, "error": str(e)}

    results = await asyncio.gather(*[score_one(f) for f in files])
    return safe_json({"scores": list(results)})


# ---------- GPS ----------

@app.post("/api/geo")
async def api_geo(file: UploadFile = File(...)):
    """استخراج مختصات GPS + Reverse Geocoding"""
    contents = await file.read()
    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = await asyncio.to_thread(extract_metadata, tmp_path)
        result.filename = file.filename
        deduped = dedup_entries(result.entries)
        gps = extract_gps_from_entries(deduped)
        if not gps:
            return safe_json({"has_gps": False})

        place = await asyncio.to_thread(reverse_geocode, gps["lat"], gps["lon"])
        gps["place"] = place["display_name"] if place else None
        gps["city"] = place["city"] if place else None
        gps["country"] = place["country"] if place else None
        gps["has_gps"] = True
        return safe_json(gps)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------- PDF Report ----------

@app.post("/api/report/pdf")
async def api_report_pdf(file: UploadFile = File(...)):
    """تولید گزارش PDF"""
    contents = await file.read()
    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = await asyncio.to_thread(extract_metadata, tmp_path)
        result.filename = file.filename
        deduped = dedup_entries(result.entries)

        geo_info = extract_gps_from_entries(deduped)
        if geo_info:
            place = await asyncio.to_thread(
                reverse_geocode, geo_info["lat"], geo_info["lon"])
            if place:
                geo_info["place"] = place.get("display_name")

        pdf_bytes = await asyncio.to_thread(
            generate_pdf_report, result, geo_info, True, 200)

        filename = f"report_{Path(file.filename).stem}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"خطا در تولید PDF: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------- Edit Metadata ----------

@app.post("/api/edit")
async def api_edit(
    file: UploadFile = File(...),
    changes: str = Form(...),
):
    """ویرایش متادیتا و برگرداندن فایل ویرایش‌شده"""
    contents = await file.read()
    suffix = Path(file.filename).suffix or ".jpg"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    out_path = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix,
        prefix=f"edited_{Path(file.filename).stem}_"
    ).name

    try:
        changes_dict = json.loads(changes)
        if not isinstance(changes_dict, dict):
            raise ValueError("changes باید یک dict باشد")

        await asyncio.to_thread(
            edit_image_metadata, tmp_path, out_path, changes_dict
        )

        edited_name = f"edited_{file.filename}"
        with open(out_path, "rb") as f:
            data = f.read()

        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{edited_name}"'},
        )
    except Exception as e:
        raise HTTPException(500, f"خطا در ویرایش: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)


# ---------- Compare ----------

@app.post("/api/compare")
async def api_compare(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    """مقایسه دو فایل"""
    async def _load(upload):
        contents = await upload.read()
        suffix = Path(upload.filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            return tmp.name, upload.filename

    path_a, name_a = await _load(file_a)
    path_b, name_b = await _load(file_b)

    try:
        result_a = await asyncio.to_thread(extract_metadata, path_a)
        result_a.filename = name_a
        result_b = await asyncio.to_thread(extract_metadata, path_b)
        result_b.filename = name_b

        diff = compare_results(result_a, result_b)
        return safe_json(diff)
    finally:
        Path(path_a).unlink(missing_ok=True)
        Path(path_b).unlink(missing_ok=True)