"""
SSCASN Explorer 2026
Data diambil langsung dari API resmi BKN: api-sscasn.bkn.go.id/2026/
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
import math
from datetime import datetime

# âââââââââââââââââââââââââââââââââââââââââââââ
#  KONFIGURASI HALAMAN
# âââââââââââââââââââââââââââââââââââââââââââââ
st.set_page_config(
    page_title="SSCASN Explorer 2026",
    page_icon="ðï¸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# âââââââââââââââââââââââââââââââââââââââââââââ
#  CSS KUSTOM
# âââââââââââââââââââââââââââââââââââââââââââââ
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.app-header {
    background: linear-gradient(135deg, #1a56db 0%, #0e3f9a 100%);
    color: white;
    padding: 28px 32px;
    border-radius: 16px;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(26,86,219,0.3);
}
.app-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.app-header p  { margin: 8px 0 0; opacity: 0.85; font-size: 0.97rem; }

.metric-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.metric-card .value { font-size: 2rem; font-weight: 700; color: #1a56db; }
.metric-card .label { font-size: 0.82rem; color: #6b7280; margin-top: 4px; font-weight: 500; }

.detail-card {
    background: #f8faff;
    border: 1px solid #dbeafe;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 16px;
}
.detail-card h3 { margin: 0 0 16px; color: #1a56db; font-size: 1.05rem; }
.detail-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.detail-item {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px 16px;
    min-width: 140px;
    flex: 1;
}
.detail-item .di-label { font-size: 0.75rem; color: #6b7280; font-weight: 600; text-transform: uppercase; }
.detail-item .di-value { font-size: 1.05rem; font-weight: 700; color: #111827; margin-top: 4px; }

.status-ok   { background:#ecfdf5; border-left:4px solid #10b981; padding:10px 16px;
               border-radius:6px; margin:8px 0; font-size:0.9rem; color:#065f46; }
.status-warn { background:#fffbeb; border-left:4px solid #f59e0b; padding:10px 16px;
               border-radius:6px; margin:8px 0; font-size:0.9rem; color:#92400e; }
.status-err  { background:#fef2f2; border-left:4px solid #ef4444; padding:10px 16px;
               border-radius:6px; margin:8px 0; font-size:0.9rem; color:#991b1b; }

section[data-testid="stSidebar"] { background: #f8fafc; }
section[data-testid="stSidebar"] label { font-weight: 600; font-size: 0.88rem; color: #374151; }
</style>
""", unsafe_allow_html=True)

# âââââââââââââââââââââââââââââââââââââââââââââ
#  KONSTANTA API (real endpoints dari BKN)
# âââââââââââââââââââââââââââââââââââââââââââââ
API_BASE = "https://api-sscasn.bkn.go.id/2026"

# Header wajib â tanpa Referer dari domain SSCASN, server BKN menolak request
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://sscasn.bkn.go.id/",
    "Origin" : "https://sscasn.bkn.go.id",
    "Accept" : "application/json, text/plain, */*",
}

# Mapping field API â label kolom Indonesia
COL_MAP = {
    "ins_nm"           : "Instansi",
    "jp_nama"          : "Jenis Pengadaan",
    "formasi_nm"       : "Jenis Formasi",
    "jabatan_nm"       : "Nama Jabatan",
    "lokasi_nm"        : "Lokasi / Unit Kerja",
    "jumlah_formasi"   : "Jumlah Formasi",
    "gaji_min"         : "Gaji Min",
    "gaji_max"         : "Gaji Maks",
    "jumlah_ms"        : "Peserta Lulus Seleksi",
    "formasi_id"       : "ID Formasi",
    "disable"          : "Status Aktif",
    "is_periode_daftar": "Periode Daftar",
}

# âââââââââââââââââââââââââââââââââââââââââââââ
#  FUNGSI FETCH DATA
# âââââââââââââââââââââââââââââââââââââââââââââ
@st.cache_data(ttl=900, show_spinner=False)
def _fetch_page(offset: int, limit: int, extra_params: str) -> dict:
    """Ambil satu halaman dari /portal/spf."""
    params = {"offset": offset, "limit": limit}
    if extra_params:
        for pair in extra_params.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if v:
                    params[k] = v
    resp = requests.get(
        f"{API_BASE}/portal/spf",
        headers=HEADERS,
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_formasi(
    jp_nama: str = "",
    ins_nm: str = "",
    max_pages: int = 50,
) -> tuple[pd.DataFrame, int]:
    """
    Ambil semua halaman formasi dari API SSCASN.
    Kembalikan (DataFrame, total_server).
    """
    limit = 100
    extra = "&".join(
        f"{k}={v}" for k, v in [
            ("jp_nama", jp_nama),
            ("ins_nm",  ins_nm),
        ] if v
    )

    first      = _fetch_page(0, limit, extra)
    meta       = first.get("meta", {})
    total      = int(meta.get("total_count", meta.get("total", 0)))
    data       = first.get("data", [])
    total_pages = min(math.ceil(total / limit) if total else 1, max_pages)

    if total_pages > 1:
        bar = st.progress(1 / total_pages, text=f"Mengunduh dataâ¦ 1/{total_pages} halaman")
        for page in range(1, total_pages):
            try:
                result = _fetch_page(page * limit, limit, extra)
                data.extend(result.get("data", []))
                bar.progress((page + 1) / total_pages,
                             text=f"Mengunduh dataâ¦ {page+1}/{total_pages} halaman")
                time.sleep(0.08)
            except Exception:
                break
        bar.empty()

    return pd.DataFrame(data), total


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rename kolom, perbaiki tipe data, bersihkan nilai kosong."""
    df = df.rename(columns={k: v for k, v in COL_MAP.items() if k in df.columns})

    if "Jumlah Formasi" in df.columns:
        df["Jumlah Formasi"] = pd.to_numeric(
            df["Jumlah Formasi"], errors="coerce"
        ).fillna(0).astype(int)

    if "Peserta Lulus Seleksi" in df.columns:
        df["Peserta Lulus Seleksi"] = pd.to_numeric(
            df["Peserta Lulus Seleksi"], errors="coerce"
        ).fillna(0).astype(int)

    # Simpan nilai numerik gaji sebelum diformat (untuk hitung keketatan finansial, dsb.)
    for raw_col, num_col in [("Gaji Min", "_gaji_min_num"), ("Gaji Maks", "_gaji_max_num")]:
        if raw_col in df.columns:
            df[num_col] = pd.to_numeric(df[raw_col], errors="coerce").fillna(0)

    # Gaji â format Rupiah
    for col in ["Gaji Min", "Gaji Maks"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"Rp {int(x):,}".replace(",", ".") if x and str(x).strip() not in ("", "None", "null", "0") else "-"
            )

    if "Status Aktif" in df.columns:
        df["Status Aktif"] = df["Status Aktif"].apply(
            lambda x: "â Aktif" if str(x) in ("0", "False", "false", "") else "â Nonaktif"
        )

    if "Periode Daftar" in df.columns:
        df["Periode Daftar"] = df["Periode Daftar"].apply(
            lambda x: "Buka" if str(x) in ("1", "True", "true") else "Tutup"
        )

    return df


# âââââââââââââââââââââââââââââââââââââââââââââ
#  DATA DEMO (fallback)
# âââââââââââââââââââââââââââââââââââââââââââââ
def demo_data() -> pd.DataFrame:
    """Contoh data dengan field real SSCASN 2026 untuk mode offline."""
    import random
    random.seed(42)

    jabatan_list = [
        "GURU AHLI PERTAMA - GURU BAHASA ARAB",
        "GURU AHLI PERTAMA - GURU BAHASA INGGRIS",
        "GURU AHLI PERTAMA - GURU MATEMATIKA",
        "GURU AHLI PERTAMA - GURU FISIKA",
        "GURU AHLI PERTAMA - GURU BIOLOGI",
        "GURU AHLI PERTAMA - GURU KIMIA",
        "GURU AHLI PERTAMA - GURU SEJARAH",
        "GURU AHLI PERTAMA - GURU EKONOMI",
        "GURU AHLI PERTAMA - GURU GEOGRAFI",
        "GURU AHLI PERTAMA - GURU SOSIOLOGI",
        "GURU AHLI PERTAMA - GURU PENDIDIKAN JASMANI",
        "GURU AHLI PERTAMA - GURU SENI BUDAYA",
        "GURU AHLI PERTAMA - GURU PRAKARYA",
        "GURU AHLI PERTAMA - GURU PENDIDIKAN AGAMA ISLAM",
        "GURU AHLI PERTAMA - GURU TEKNOLOGI INFORMASI",
        "ANALIS KEBIJAKAN AHLI PERTAMA",
        "PRANATA KOMPUTER AHLI PERTAMA",
        "AUDITOR AHLI PERTAMA",
    ]
    provinsi = [
        "Prov. Aceh", "Prov. Sumatera Utara", "Prov. Sulawesi Selatan",
        "Prov. Kalimantan Barat", "Prov. Jawa Tengah", "Prov. DI Yogyakarta",
        "Prov. Bali", "Prov. Maluku", "Prov. Sulawesi Utara", "Prov. Papua",
        "Prov. Nusa Tenggara Timur", "Prov. Kep. Bangka Belitung",
    ]
    formasi_type = ["UMUM", "DISABILITAS", "PUTRA/PUTRI PAPUA", "CUMLAUDE"]
    jenis_pengadaan_list = [
        "PPPK Guru", "PPPK Guru", "PPPK Guru", "PPPK Teknis", "CPNS",
    ]
    instansi_list = [
        "Kementerian Pendidikan Tinggi, Sains, dan Teknologi",
        "Kementerian Kesehatan RI",
        "Badan Kepegawaian Negara",
        "Kementerian Keuangan RI",
    ]

    rows = []
    for jab in jabatan_list:
        for _ in range(random.randint(3, 8)):
            jp = random.choice(jenis_pengadaan_list)
            rows.append({
                "Instansi"            : random.choice(instansi_list),
                "Jenis Pengadaan"     : jp,
                "Jenis Formasi"       : random.choice(formasi_type),
                "Nama Jabatan"        : jab,
                "Lokasi / Unit Kerja" : f"Unit Kerja {random.choice(provinsi)}",
                "Jumlah Formasi"      : random.randint(1, 6),
                "Gaji Min"            : "-",
                "Gaji Maks"           : "-",
                "Peserta Lulus Seleksi": random.randint(0, 20),
                "_gaji_min_num"       : 0,
                "_gaji_max_num"       : 0,
                "Status Aktif"        : "â Aktif",
                "Periode Daftar"      : "Buka",
            })
    return pd.DataFrame(rows)


# âââââââââââââââââââââââââââââââââââââââââââââ
#  HEADER
# âââââââââââââââââââââââââââââââââââââââââââââ
st.markdown("""
<div class="app-header">
    <h1>ðï¸ SSCASN Explorer 2026</h1>
    <p>Cari &amp; filter formasi PPPK / CPNS secara mudah &mdash;
       data real-time dari API resmi BKN &bull; api-sscasn.bkn.go.id/2026/</p>
</div>
""", unsafe_allow_html=True)

# âââââââââââââââââââââââââââââââââââââââââââââ
#  SIDEBAR
# âââââââââââââââââââââââââââââââââââââââââââââ
with st.sidebar:
    st.markdown("## ð Filter & Pencarian")

    mode = st.radio(
        "Sumber Data",
        ["ð API Live BKN", "ð¦ Data Demo (Offline)"],
        help="'API Live' mengambil data real-time dari server BKN."
    )
    use_live = "Live" in mode

    st.divider()

    jp_pilihan = st.selectbox(
        "Jenis Pengadaan",
        ["Semua", "PPPK Guru", "PPPK Teknis", "PPPK Kesehatan", "CPNS"],
    )
    jp_param = "" if jp_pilihan == "Semua" else jp_pilihan

    formasi_pilihan = st.selectbox(
        "Jenis Formasi",
        ["Semua", "UMUM", "DISABILITAS", "PUTRA/PUTRI PAPUA", "CUMLAUDE"],
    )

    cari_instansi = st.text_input(
        "Cari Instansi",
        placeholder="Contoh: Pendidikan, Kesehatanâ¦"
    )
    cari_lokasi = st.text_input(
        "Cari Lokasi / Provinsi",
        placeholder="Contoh: Papua, Jawa, Baliâ¦"
    )

    st.divider()
    st.markdown("### âï¸ Pengaturan")
    max_pages = st.slider(
        "Maks. halaman diunduh",
        min_value=1, max_value=100, value=10,
        help="1 halaman = 100 baris data."
    )
    show_charts = st.toggle("Tampilkan visualisasi", value=True)

    st.divider()
    if st.button("ð Refresh / Bersihkan Cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Update: {datetime.now().strftime('%d %b %Y, %H:%M WIB')}")
    st.caption("Data Â© Badan Kepegawaian Negara RI")

# âââââââââââââââââââââââââââââââââââââââââââââ
#  MUAT DATA
# âââââââââââââââââââââââââââââââââââââââââââââ
total_server = 0
use_demo     = False

if use_live:
    try:
        with st.spinner("â³ Menghubungi server BKNâ¦"):
            df_raw, total_server = fetch_all_formasi(
                jp_nama   = jp_param,
                ins_nm    = cari_instansi,
                max_pages = max_pages,
            )
        if df_raw.empty:
            st.markdown(
                '<div class="status-warn">â ï¸ API tidak mengembalikan data '
                '(mungkin belum ada formasi aktif). Menampilkan data demo.</div>',
                unsafe_allow_html=True,
            )
            df_raw   = demo_data()
            use_demo = True
        else:
            df_raw = clean_df(df_raw)
            st.markdown(
                f'<div class="status-ok">â Data live dari BKN â '
                f'<strong>{total_server:,}</strong> formasi tersedia di server '
                f'(diunduh {len(df_raw):,} baris).</div>',
                unsafe_allow_html=True,
            )
    except requests.exceptions.ConnectionError:
        st.markdown(
            '<div class="status-err">â Tidak bisa terhubung ke server BKN. '
            'Menampilkan data demo.</div>',
            unsafe_allow_html=True,
        )
        df_raw   = demo_data()
        use_demo = True
    except Exception as e:
        st.markdown(
            f'<div class="status-err">â Error: {e} â Menampilkan data demo.</div>',
            unsafe_allow_html=True,
        )
        df_raw   = demo_data()
        use_demo = True
else:
    df_raw   = demo_data()
    use_demo = True
    st.markdown(
        '<div class="status-warn">ð¦ Mode Demo â data ini hanya ilustrasi, '
        'bukan data real dari BKN. Pilih "API Live" untuk data terkini.</div>',
        unsafe_allow_html=True,
    )

# âââââââââââââââââââââââââââââââââââââââââââââ
#  FILTER LOKAL
# âââââââââââââââââââââââââââââââââââââââââââââ
df = df_raw.copy()

if jp_pilihan != "Semua" and "Jenis Pengadaan" in df.columns:
    df = df[df["Jenis Pengadaan"].str.contains(jp_pilihan, case=False, na=False)]

if formasi_pilihan != "Semua" and "Jenis Formasi" in df.columns:
    df = df[df["Jenis Formasi"].str.contains(formasi_pilihan, case=False, na=False)]

if cari_lokasi and "Lokasi / Unit Kerja" in df.columns:
    df = df[df["Lokasi / Unit Kerja"].str.contains(cari_lokasi, case=False, na=False)]

if use_demo and cari_instansi and "Instansi" in df.columns:
    df = df[df["Instansi"].str.contains(cari_instansi, case=False, na=False)]

# âââââââââââââââââââââââââââââââââââââââââââââ
#  FILTER JABATAN â MULTISELECT
# âââââââââââââââââââââââââââââââââââââââââââââ
if "Nama Jabatan" in df.columns and not df.empty:
    all_jabatan = sorted([
        j for j in df["Nama Jabatan"].dropna().unique()
        if "S-1 Pendidikan" not in str(j)
    ])
    selected_jabatan = st.multiselect(
        "ð Filter Jabatan / Jurusan (pilih satu atau lebih)",
        options=all_jabatan,
        default=[],
        placeholder="Ketik untuk mencari jabatan, atau pilih dari daftarâ¦",
    )
    if selected_jabatan:
        df = df[df["Nama Jabatan"].isin(selected_jabatan)]

# âââââââââââââââââââââââââââââââââââââââââââââ
#  METRIK RINGKASAN
# âââââââââââââââââââââââââââââââââââââââââââââ
total_lowongan = int(df["Jumlah Formasi"].sum()) if "Jumlah Formasi" in df.columns else len(df)
total_instansi = df["Instansi"].nunique()         if "Instansi"       in df.columns else 0
total_jabatan  = df["Nama Jabatan"].nunique()     if "Nama Jabatan"   in df.columns else 0

c1, c2, c3, c4 = st.columns(4)
for col, val, label in [
    (c1, len(df),        "Baris Formasi"),
    (c2, total_lowongan, "Total Lowongan"),
    (c3, total_instansi, "Instansi"),
    (c4, total_jabatan,  "Jenis Jabatan"),
]:
    col.markdown(f"""
    <div class="metric-card">
        <div class="value">{val:,}</div>
        <div class="label">{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# âââââââââââââââââââââââââââââââââââââââââââââ
#  VISUALISASI
# âââââââââââââââââââââââââââââââââââââââââââââ
if show_charts and not df.empty:
    st.subheader("ð Visualisasi")
    tab1, tab2, tab3 = st.tabs(
        ["ð« Sebaran per Jabatan", "ðï¸ Jenis Formasi", "ðºï¸ Sebaran Lokasi"]
    )

    with tab1:
        if "Nama Jabatan" in df.columns and "Jumlah Formasi" in df.columns:
            n = st.slider("Tampilkan N jabatan teratas", 5, min(30, len(df)), min(15, len(df)), key="sl1")
            top_jab = (
                df.groupby("Nama Jabatan")["Jumlah Formasi"]
                .sum().nlargest(n).reset_index().sort_values("Jumlah Formasi")
            )
            top_jab["Label"] = top_jab["Nama Jabatan"].str.replace(
                "GURU AHLI PERTAMA - ", "", regex=False
            ).str.title()
            fig = px.bar(
                top_jab, x="Jumlah Formasi", y="Label",
                orientation="h", color="Jumlah Formasi",
                color_continuous_scale="Blues",
                labels={"Jumlah Formasi": "Jumlah Lowongan", "Label": ""},
                title=f"Top {n} Jabatan berdasarkan Jumlah Formasi",
            )
            fig.update_layout(
                height=max(380, n * 28), coloraxis_showscale=False,
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="Inter", title_font_size=14,
            )
            fig.update_traces(hovertemplate="<b>%{y}</b><br>Lowongan: %{x}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if "Jenis Formasi" in df.columns and "Jumlah Formasi" in df.columns:
            pie_data = df.groupby("Jenis Formasi")["Jumlah Formasi"].sum().reset_index()
            fig2 = px.pie(
                pie_data, names="Jenis Formasi", values="Jumlah Formasi",
                title="Distribusi Lowongan berdasarkan Jenis Formasi",
                color_discrete_sequence=px.colors.qualitative.Safe,
                hole=0.42,
            )
            fig2.update_traces(
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>%{value} lowongan (%{percent})<extra></extra>",
            )
            fig2.update_layout(font_family="Inter", title_font_size=14)
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        if "Lokasi / Unit Kerja" in df.columns and "Jumlah Formasi" in df.columns:
            def extract_provinsi(s: str) -> str:
                s = str(s)
                if "Prov." in s:
                    return s.split("Prov.")[-1].strip()
                if "Provinsi" in s:
                    return s.split("Provinsi")[-1].strip()
                parts = s.split(",")
                return parts[-1].strip() if len(parts) > 1 else s

            df_loc = df.copy()
            df_loc["Provinsi"] = df_loc["Lokasi / Unit Kerja"].apply(extract_provinsi)
            prov_data = (
                df_loc.groupby("Provinsi")["Jumlah Formasi"]
                .sum().nlargest(20).reset_index()
            )
            fig3 = px.bar(
                prov_data, x="Provinsi", y="Jumlah Formasi",
                color="Jumlah Formasi", color_continuous_scale="Teal",
                title="Jumlah Formasi per Provinsi (Top 20)",
                labels={"Jumlah Formasi": "Jumlah Lowongan", "Provinsi": ""},
            )
            fig3.update_layout(
                xaxis_tickangle=-35, coloraxis_showscale=False,
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="Inter", title_font_size=14, height=420,
            )
            st.plotly_chart(fig3, use_container_width=True)

    st.divider()

# âââââââââââââââââââââââââââââââââââââââââââââ
#  TABEL INTERAKTIF â CPNS & PPPK
# âââââââââââââââââââââââââââââââââââââââââââââ
st.subheader("ð Daftar Formasi")
st.caption("Klik baris untuk melihat detail lengkap formasi tersebut.")

# Pencarian cepat
q = st.text_input("ð Cari di seluruh tabel", placeholder="Ketik kata kunciâ¦", key="q")
df_show = df.copy()
if q:
    str_cols = [c for c in df_show.columns if not c.startswith("_")]
    mask = df_show[str_cols].apply(
        lambda col: col.astype(str).str.contains(q, case=False, na=False)
    ).any(axis=1)
    df_show = df_show[mask]

st.caption(f"Menampilkan **{len(df_show):,}** dari {len(df):,} baris formasi")


def render_detail_panel(row: pd.Series):
    """Tampilkan panel detail saat sebuah baris dipilih."""
    jabatan   = row.get("Nama Jabatan", "-")
    instansi  = row.get("Instansi", "-")
    lokasi    = row.get("Lokasi / Unit Kerja", "-")
    jenis_f   = row.get("Jenis Formasi", "-")
    jenis_p   = row.get("Jenis Pengadaan", "-")
    kuota     = row.get("Jumlah Formasi", 0)
    gaji_min  = row.get("Gaji Min", "-")
    gaji_maks = row.get("Gaji Maks", "-")
    peserta   = row.get("Peserta Lulus Seleksi", 0)
    periode   = row.get("Periode Daftar", "-")

    # Hitung keketatan
    try:
        kuota_num   = int(kuota) if kuota else 0
        peserta_num = int(peserta) if peserta else 0
        if kuota_num > 0:
            keketatan = peserta_num / kuota_num
            ket_str   = f"{keketatan:.1f}Ã ({peserta_num} pelamar / {kuota_num} kursi)"
        else:
            ket_str = "Belum ada data"
    except Exception:
        ket_str = "Belum ada data"

    with st.container():
        st.markdown(f"""
<div class="detail-card">
  <h3>ð Detail: {jabatan}</h3>
  <div style="color:#374151;font-size:0.88rem;margin-bottom:14px;">
    <strong>{instansi}</strong>
  </div>
  <div class="detail-row">
    <div class="detail-item">
      <div class="di-label">Kuota / Formasi</div>
      <div class="di-value">{kuota} kursi</div>
    </div>
    <div class="detail-item">
      <div class="di-label">Keketatan</div>
      <div class="di-value">{ket_str}</div>
    </div>
    <div class="detail-item">
      <div class="di-label">Gaji Minimal</div>
      <div class="di-value">{gaji_min}</div>
    </div>
    <div class="detail-item">
      <div class="di-label">Gaji Maksimal</div>
      <div class="di-value">{gaji_maks}</div>
    </div>
  </div>
  <div class="detail-row">
    <div class="detail-item">
      <div class="di-label">Lokasi / Unit Kerja</div>
      <div class="di-value" style="font-size:0.92rem">{lokasi}</div>
    </div>
    <div class="detail-item">
      <div class="di-label">Jenis Formasi</div>
      <div class="di-value">{jenis_f}</div>
    </div>
    <div class="detail-item">
      <div class="di-label">Jenis Pengadaan</div>
      <div class="di-value">{jenis_p}</div>
    </div>
    <div class="detail-item">
      <div class="di-label">Periode Daftar</div>
      <div class="di-value">{periode}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Grafik keketatan lintas formasi untuk jabatan yang sama
    same_jabatan = df[df["Nama Jabatan"] == jabatan].copy() if "Nama Jabatan" in df.columns else pd.DataFrame()
    if len(same_jabatan) > 1 and "Jumlah Formasi" in same_jabatan.columns:
        st.markdown("**ð Keketatan di seluruh lokasi untuk jabatan ini**")
        try:
            same_jabatan["Peserta Lulus Seleksi"] = pd.to_numeric(
                same_jabatan.get("Peserta Lulus Seleksi", 0), errors="coerce"
            ).fillna(0)
            same_jabatan["Jumlah Formasi"] = pd.to_numeric(
                same_jabatan["Jumlah Formasi"], errors="coerce"
            ).fillna(0)
            same_jabatan = same_jabatan[same_jabatan["Jumlah Formasi"] > 0].copy()
            same_jabatan["Keketatan"] = (
                same_jabatan["Peserta Lulus Seleksi"] / same_jabatan["Jumlah Formasi"]
            ).round(2)

            lok_col  = "Lokasi / Unit Kerja" if "Lokasi / Unit Kerja" in same_jabatan.columns else None
            x_label  = lok_col or "index"
            same_jabatan["Lokasi Label"] = (
                same_jabatan[lok_col].str[:40] + "â¦"
                if lok_col else same_jabatan.index.astype(str)
            )
            fig_kek = px.bar(
                same_jabatan.sort_values("Keketatan", ascending=False).head(15),
                x="Lokasi Label", y="Keketatan",
                color="Keketatan", color_continuous_scale="Reds",
                labels={"Lokasi Label": "Lokasi", "Keketatan": "Tingkat Keketatan (Ã)"},
                title="Keketatan per Lokasi (pelamar Ã· kursi)",
            )
            fig_kek.update_layout(
                xaxis_tickangle=-30, coloraxis_showscale=False,
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="Inter", title_font_size=13, height=360,
            )
            st.plotly_chart(fig_kek, use_container_width=True)
        except Exception:
            st.info("Grafik keketatan tidak dapat ditampilkan.")

    st.info("ð¡ Data historis tahun sebelumnya belum tersedia di API SSCASN 2026. Grafik tahun ke tahun akan muncul otomatis jika data multi-tahun tersedia.")


def render_formasi_tab(df_tab: pd.DataFrame, tab_key: str):
    """Render tabel dengan dua kolom + panel detail."""
    if df_tab.empty:
        st.info("Tidak ada data untuk kategori ini dengan filter yang dipilih.")
        return

    tbl_cols   = [c for c in ["Instansi", "Nama Jabatan"] if c in df_tab.columns]
    df_display = df_tab[tbl_cols].reset_index(drop=True)

    col_cfg = {
        "Instansi"    : st.column_config.TextColumn("Instansi", width="large"),
        "Nama Jabatan": st.column_config.TextColumn("Nama Jabatan / Posisi", width="large"),
    }

    selection = st.dataframe(
        df_display,
        use_container_width=True,
        height=420,
        column_config=col_cfg,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"tbl_{tab_key}",
    )

    selected_rows = selection.selection.rows if hasattr(selection, "selection") and selection.selection else []
    if selected_rows:
        idx = selected_rows[0]
        row = df_tab.reset_index(drop=True).iloc[idx]
        render_detail_panel(row)
    else:
        st.markdown(
            "<p style='color:#9ca3af;font-size:0.85rem;margin-top:8px;'>"
            "ð Klik salah satu baris untuk melihat detail formasi (gaji, kuota, keketatan, dll.)"
            "</p>",
            unsafe_allow_html=True,
        )


# Pisah CPNS dan PPPK
if "Jenis Pengadaan" in df_show.columns:
    df_pppk = df_show[df_show["Jenis Pengadaan"].str.contains("PPPK", case=False, na=False)]
    df_cpns = df_show[df_show["Jenis Pengadaan"].str.contains("CPNS", case=False, na=False)]
    df_lain = df_show[
        ~df_show["Jenis Pengadaan"].str.contains("PPPK|CPNS", case=False, na=False)
    ]
else:
    df_pppk = df_show
    df_cpns = pd.DataFrame()
    df_lain = pd.DataFrame()

n_pppk = len(df_pppk)
n_cpns = len(df_cpns)

tab_label_pppk = f"ð PPPK ({n_pppk:,})"
tab_label_cpns = f"ð CPNS ({n_cpns:,})"

tab_pppk, tab_cpns = st.tabs([tab_label_pppk, tab_label_cpns])

with tab_pppk:
    render_formasi_tab(df_pppk, "pppk")

with tab_cpns:
    render_formasi_tab(df_cpns, "cpns")

# âââââââââââââââââââââââââââââââââââââââââââââ
#  EKSPOR DATA
# âââââââââââââââââââââââââââââââââââââââââââââ
st.divider()
st.subheader("â¬ï¸ Unduh Data")
ts = datetime.now().strftime("%Y%m%d_%H%M")

# Kolom ekspor b tanpa kolom internal
export_cols = [c for c in df_show.columns if not c.startswith("_")]
df_export   = df_show[export_cols]

c1, c2, c3 = st.columns(3)

csv_bytes = df_export.to_csv(index=False).encode("utf-8-sig")
with c1:
    st.download_button(
        "ð¥ Unduh CSV", data=csv_bytes,
        file_name=f"formasi_sscasn_{ts}.csv", mime="text/csv",
        use_container_width=True,
    )

try:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_export.to_excel(w, index=False, sheet_name="Formasi SSCASN 2026")
    with c2:
        st.download_button(
            "ð Unduh Excel", data=buf.getvalue(),
            file_name=f"formasi_sscasn_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
except ImportError:
    with c2:
        st.info("Install openpyxl untuk ekspor Excel.")

json_bytes = df_export.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
with c3:
    st.download_button(
        "ð Unduh JSON", data=json_bytes,
        file_name=f"formasi_sscasn_{ts}.json", mime="application/json",
        use_container_width=True,
    )

# âââââââââââââââââââââââââââââââââââââââââââââ
#  RINGKASAN PER JABATAN
# âââââââââââââââââââââââââââââââââââââââââââââ
if "Nama Jabatan" in df.columns and "Jumlah Formasi" in df.columns:
    st.divider()
    st.subheader("ð Ringkasan per Jabatan")
    grp_cols = ["Nama Jabatan"]
    if "Jenis Formasi" in df.columns:
        grp_cols.append("Jenis Formasi")
    agg_dict = {"Jumlah Formasi": "sum"}
    if "Lokasi / Unit Kerja" in df.columns:
        agg_dict["Lokasi / Unit Kerja"] = "nunique"
    summ = (
        df.groupby(grp_cols).agg(agg_dict)
        .reset_index()
        .sort_values("Jumlah Formasi", ascending=False)
        .rename(columns={"Jumlah Formasi": "Total Lowongan", "Lokasi / Unit Kerja": "Jumlah Lokasi"})
    )
    summ["Nama Jabatan"] = summ["Nama Jabatan"].str.replace(
        "GURU AHLI PERTAMA - ", "", regex=False
    ).str.title()
    st.dataframe(
        summ, use_container_width=True, hide_index=True,
        column_config={"Total Lowongan": st.column_config.NumberColumn(format="%d")}
    )

# âââââââââââââââââââââââââââââââââââââââââââââ
#  INFO API & TROUBLESHOOTING
# âââââââââââââââââââââââââââââââââââââââââââââ
with st.expander("â¹ï¸ Info API & Troubleshooting"):
    st.markdown(f"""
**Endpoint yang digunakan:**
- Formasi : `{API_BASE}/portal/spf?offset=0&limit=100`

**Header wajib untuk setiap request:**
```
Referer: https://sscasn.bkn.go.id/
Origin:  https://sscasn.bkn.go.id
```
Tanpa header ini, server BKN akan menolak request dengan error CORS/403.

**Kondisi saat ini (April 2026):**
- Hanya sebagian instansi yang sudah membuka formasi
- Formasi CPNS/PPPK instansi lain mungkin belum dibuka

**Jika terjadi error:**
- Pastikan ada koneksi internet
- Coba klik "Refresh / Bersihkan Cache" di sidebar
- Jika server BKN sedang maintenance, gunakan mode "Data Demo"
""")

# âââââââââââââââââââââââââââââââââââââââââââââ
#  FOOTER
# âââââââââââââââââââââââââââââââââââââââââââââ
st.divider()
st.markdown("""
<div style="text-align:center;color:#9ca3af;font-size:0.82rem;padding:8px 0 24px">
    Data bersumber dari
    <a href="https://sscasn.bkn.go.id" target="_blank" style="color:#6b7280;">
        SSCASN â Badan Kepegawaian Negara RI
    </a>
    &nbsp;|&nbsp; Aplikasi ini bukan produk resmi BKN
    &nbsp;|&nbsp; Selalu verifikasi ke sumber resmi sebelum mendaftar
</div>
""", unsafe_allow_html=True)
