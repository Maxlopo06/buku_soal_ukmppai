import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime

# --- 1. Konfigurasi Halaman ---
st.set_page_config(page_title="Sistem Editor & Statistik Soal", layout="wide")

# --- UPDATE JUDUL ---
st.title("📚 TO UKMPPAI - Pilih Soal & Statistik Buku Soal")

# --- CSS UNTUK MEMPERBESAR FONT TAB & VISUALISASI ---
st.markdown("""
<style>
    /* Mengubah ukuran font pada label Tab */
    button[data-baseweb="tab"] div p {
        font-size: 22px !important;
        font-weight: bold !important;
    }
    button[data-baseweb="tab"] {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- KONFIGURASI FILE & WAKTU ---
RECOVERY_FILE = "recovery_data.csv"
AUTO_SAVE_INTERVAL = 600  # 600 detik = 10 menit
MAX_QUOTA = 200 # Batas maksimal soal per buku

# Inisialisasi state
if 'last_save_time' not in st.session_state:
    st.session_state['last_save_time'] = time.time()

# --- 2. Input Data (Dipindah ke Expander) ---
with st.expander("📂 PANEL INPUT DATA (Klik di sini untuk Sembunyikan/Tampilkan)", expanded=True):
    st.info("Silakan upload file Soal dan Referensi di bawah ini.")
    col_upload_1, col_upload_2 = st.columns(2)
    
    with col_upload_1:
        file_utama = st.file_uploader("1. Upload File Soal (Utama)", type=['csv', 'xlsx'])
    with col_upload_2:
        file_ref = st.file_uploader("2. Upload File Referensi (Tinjauan)", type=['csv', 'xlsx'])

def load_data(file):
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        else:
            return pd.read_excel(file)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

if file_utama and file_ref:
    # A. Load Data
    df_soal = load_data(file_utama)
    df_ref = load_data(file_ref)

    if df_soal is not None and df_ref is not None:
        
        # --- LOGIKA NORMALISASI KOLOM BUKU (FITUR BARU) ---
        # Mengubah input angka (1, 2, 3...) menjadi format "Buku 1", "Buku 2"...
        if 'Buku' in df_soal.columns:
            def format_buku(val):
                if pd.isna(val): 
                    return val
                # Ubah ke string, hapus spasi dan .0 (jika format float)
                val_str = str(val).strip().replace('.0', '')
                
                # Cek jika isinya hanya angka 1-6
                if val_str.isdigit():
                    angka = int(val_str)
                    if 1 <= angka <= 6:
                        return f"Buku {angka}"
                
                # Jika user sudah menulis "Buku 1", biarkan saja
                return val

            # Terapkan fungsi ke seluruh kolom Buku
            df_soal['Buku'] = df_soal['Buku'].apply(format_buku)

        # --- LOGIKA AUTO-RECOVERY ---
        if os.path.exists(RECOVERY_FILE):
            mod_time = os.path.getmtime(RECOVERY_FILE)
            waktu_backup = datetime.fromtimestamp(mod_time).strftime('%H:%M:%S')
            
            st.warning(f"⚠️ Ditemukan pekerjaan yang belum selesai (Pukul {waktu_backup}).")
            col_rec_1, col_rec_2 = st.columns([1, 4])
            with col_rec_1:
                if st.button("📂 Pakai Data Backup"):
                    df_soal = pd.read_csv(RECOVERY_FILE)
                    st.toast("Data backup berhasil dimuat!", icon="✅")
            with col_rec_2:
                if st.button("🗑️ Hapus & Mulai Baru"):
                    os.remove(RECOVERY_FILE)
                    st.rerun()

        # --- 3. Persiapan Data & Konfigurasi Kolom ---
        
        # 1. Opsi Buku (Hanya 1-6)
        opsi_buku = [f"Buku {i}" for i in range(1, 7)]
        
        # 2. Deteksi Kolom Tinjauan di File Soal
        tinjauan_cols = [col for col in df_soal.columns if 'Tinjauan' in col]

        # 3. Konfigurasi Awal (Kolom Buku)
        column_config = {
            "Buku": st.column_config.SelectboxColumn(
                "Pilih Buku", 
                width="medium", 
                options=opsi_buku, 
                required=False 
            )
        }
        
        # 4. Konfigurasi Kolom Tinjauan (Dropdown dari Referensi)
        for col in tinjauan_cols:
            if col in df_ref.columns:
                opsi_referensi = sorted(df_ref[col].dropna().unique().tolist())
                column_config[col] = st.column_config.SelectboxColumn(
                    label=col,             
                    width="large",         
                    options=opsi_referensi,
                    required=False         
                )

        # --- 4. Tabs ---
        tab_editor, tab_stats = st.tabs(["✏️ Editor Data", "📊 Dashboard Statistik"])

        # === TAB 1: EDITOR ===
        with tab_editor:
            col_header_1, col_header_2 = st.columns([3, 1])
            with col_header_1:
                st.subheader("Edit Data Soal")
            with col_header_2:
                tombol_simpan = st.button("💾 Simpan Progres Sekarang", type="primary")

            col_search_1, col_search_2 = st.columns([3, 1])
            with col_search_1:
                search_query = st.text_input("🔍 Cari Data (Ketik kata kunci):", "")
            
            if search_query:
                mask = df_soal.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                df_display = df_soal[mask]
                st.info(f"Menampilkan {len(df_display)} data yang cocok dengan '{search_query}'")
            else:
                df_display = df_soal

            # --- EDITOR UTAMA ---
            df_edited = st.data_editor(
                df_display,
                column_config=column_config, 
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="editor_soal"
            )
            
            # --- VALIDASI KUOTA ---
            df_valid_books = df_edited[df_edited['Buku'].notna()]
            counts = df_valid_books['Buku'].value_counts()
            buku_overload = counts[counts > MAX_QUOTA].index.tolist()
            is_valid = len(buku_overload) == 0

            # --- LOGIKA PENYIMPANAN ---
            if not is_valid:
                st.error(f"⛔ **PERINGATAN KERAS: KUOTA PENUH!**")
                st.error(f"Buku berikut telah melebihi {MAX_QUOTA} soal: {', '.join(buku_overload)}")
                st.warning("⚠️ **Sistem Penyimpanan Dihentikan Sementara.**")
            
            else:
                if not search_query:
                    current_time = time.time()
                    time_diff = current_time - st.session_state['last_save_time']
                    
                    if tombol_simpan or time_diff > AUTO_SAVE_INTERVAL:
                        df_edited.to_csv(RECOVERY_FILE, index=False)
                        st.session_state['last_save_time'] = current_time
                        
                        waktu_simpan = datetime.fromtimestamp(current_time).strftime('%H:%M:%S')
                        if tombol_simpan:
                            st.toast(f"Tersimpan Manual pada {waktu_simpan}", icon="💾")
                        else:
                            st.toast(f"Auto-save berhasil ({waktu_simpan})", icon="⏰")

                    sisa_waktu = int(AUTO_SAVE_INTERVAL - time_diff)
                    if sisa_waktu < 0: sisa_waktu = 0
                    st.caption(f"⏱️ Auto-save aktif (Tersimpan: {datetime.fromtimestamp(st.session_state['last_save_time']).strftime('%H:%M:%S')})")

            st.write("---")
            
            if is_valid:
                if search_query:
                    st.warning("⚠️ Perhatian: Sedang memfilter. Download hanya hasil pencarian.")
                
                csv_buffer = df_edited.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download Data Final (CSV)",
                    data=csv_buffer,
                    file_name="buku_soal_terupdate.csv",
                    mime="text/csv",
                )
            else:
                st.button("⛔ Download Dikunci (Perbaiki Kuota Dulu)", disabled=True)

        # === TAB 2: STATISTIK ===
        with tab_stats:
            st.header("Analisis Komprehensif")
            data_untuk_stats = df_edited if not search_query else df_soal
            
            # A. Progress Kuota
            st.subheader(f"1. Progress Kuota (Target: {MAX_QUOTA}/Buku)")
            
            # --- MODIFIKASI: FILTER BERDASARKAN BIDANG ILMU ---
            df_grafik = data_untuk_stats[data_untuk_stats['Buku'].notna()]
            
            # Variabel judul default
            judul_grafik = "Status Kuota Buku (Total Keseluruhan)"
            
            # Cek apakah kolom 'BidangIlmu' ada di data (Case Sensitive sesuai excel)
            if 'BidangIlmu' in df_grafik.columns:
                # Ambil daftar unik bidang ilmu, tambah opsi 'Semua'
                list_bidang = ['Semua'] + sorted(df_grafik['BidangIlmu'].dropna().astype(str).unique().tolist())
                
                col_filter_1, col_filter_2 = st.columns([1, 3])
                with col_filter_1:
                    # Widget Selectbox
                    pilih_bidang = st.selectbox("🔍 Filter Bidang Ilmu:", list_bidang)
                
                # Terapkan filter jika bukan 'Semua'
                if pilih_bidang != 'Semua':
                    df_grafik = df_grafik[df_grafik['BidangIlmu'] == pilih_bidang]
                    judul_grafik = f"Status Kuota Buku - Bidang: {pilih_bidang}"
                    st.caption(f"ℹ️ Menampilkan data khusus untuk: **{pilih_bidang}**")
            else:
                st.warning("⚠️ Kolom 'BidangIlmu' tidak ditemukan di file. Filter tidak ditampilkan.")
            # ----------------------------------------------------

            # Hitung jumlah per buku setelah filter
            count_per_buku = df_grafik['Buku'].value_counts().reindex(opsi_buku, fill_value=0).reset_index()
            count_per_buku.columns = ['Buku', 'Jumlah Soal']
            
            # Logika pewarnaan (Merah jika > Max, Hijau jika = Max, Biru jika < Max)
            # Catatan: Jika difilter, batas MAX_QUOTA mungkin tidak relevan, tapi tetap jadi acuan visual
            colors = ['red' if x > MAX_QUOTA else 'green' if x == MAX_QUOTA else 'blue' for x in count_per_buku['Jumlah Soal']]
            
            fig_prog = px.bar(
                count_per_buku, x='Jumlah Soal', y='Buku', orientation='h', text='Jumlah Soal',
                title=judul_grafik, # Judul dinamis
            )
            fig_prog.update_traces(textfont=dict(size=16), textposition='outside', cliponaxis=False, marker_color=colors) 
            fig_prog.update_layout(font=dict(size=14)) 
            fig_prog.add_vline(x=MAX_QUOTA, line_width=3, line_dash="solid", line_color="red", annotation_text="BATAS MAKSIMAL")
            st.plotly_chart(fig_prog, use_container_width=True)
            
            # Peringatan Overload (Hanya muncul jika di 'Semua' agar tidak membingungkan saat difilter)
            if 'pilih_bidang' not in locals() or pilih_bidang == 'Semua':
                for index, row in count_per_buku.iterrows():
                    if row['Jumlah Soal'] > MAX_QUOTA:
                        st.error(f"⛔ {row['Buku']} KELEBIHAN {row['Jumlah Soal'] - MAX_QUOTA} soal! Harap dikurangi.")
            
            st.divider()

            # B. Heatmap
            st.subheader("2. Peta Sebaran (Heatmap)")
            pilihan_tinjauan = st.selectbox("Pilih Kategori Tinjauan untuk Heatmap:", tinjauan_cols)
            if pilihan_tinjauan:
                df_clean = data_untuk_stats.dropna(subset=['Buku', pilihan_tinjauan])
                df_heatmap = df_clean.groupby(['Buku', pilihan_tinjauan]).size().reset_index(name='Jumlah')
                
                if not df_heatmap.empty:
                    urutan_tinjauan = sorted(df_heatmap[pilihan_tinjauan].unique())
                    fig_heat = px.density_heatmap(
                        df_heatmap, x=pilihan_tinjauan, y="Buku", z="Jumlah", text_auto=True,
                        color_continuous_scale="Viridis",
                        category_orders={pilihan_tinjauan: urutan_tinjauan, "Buku": opsi_buku}
                    )
                    fig_heat.update_layout(xaxis_tickangle=-45, height=500, font=dict(size=14))
                    st.plotly_chart(fig_heat, use_container_width=True)
                else:
                    st.info("Belum ada data yang cukup untuk menampilkan heatmap.")
            st.divider()

            # C. Rekapitulasi Detail
            st.subheader("3. Profil Detail Per Buku")
            recap_list = []
            for col in tinjauan_cols:
                df_clean_recap = data_untuk_stats.dropna(subset=['Buku', col])
                temp = df_clean_recap.groupby(['Buku', col]).size().reset_index(name='Jumlah')
                temp.rename(columns={col: 'Isi Tinjauan'}, inplace=True)
                temp['Jenis Tinjauan'] = col 
                recap_list.append(temp[['Buku', 'Jenis Tinjauan', 'Isi Tinjauan', 'Jumlah']])
            
            if recap_list:
                df_recap = pd.concat(recap_list, ignore_index=True)
                col_profil_1, col_profil_2 = st.columns([1, 3])
                
                with col_profil_1:
                    st.markdown("#### 📘 Pilih Buku")
                    selected_book_recap = st.radio("Tampilkan Profil Untuk:", opsi_buku)
                    st.write("---")
                    csv_recap = df_recap.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download Rekap", csv_recap, "rekap.csv", "text/csv")

                with col_profil_2:
                    if selected_book_recap:
                        subset_book = df_recap[df_recap['Buku'] == selected_book_recap]
                        if not subset_book.empty:
                            st.markdown(f"### 📊 {selected_book_recap}")
                            list_jenis = sorted(subset_book['Jenis Tinjauan'].unique())
                            for jenis in list_jenis:
                                df_jenis = subset_book[subset_book['Jenis Tinjauan'] == jenis].sort_values(by="Isi Tinjauan", ascending=False)
                                
                                dynamic_height = max(200, len(df_jenis) * 35 + 80)
                                fig_item = px.bar(
                                    df_jenis, x="Jumlah", y="Isi Tinjauan", orientation='h',
                                    title=f"<b>{jenis}</b>", text_auto=True, color="Jumlah", color_continuous_scale="Blues"
                                )
                                fig_item.update_traces(textposition="outside", cliponaxis=False, textfont=dict(size=16))
                                fig_item.update_layout(
                                    height=dynamic_height, margin=dict(l=10, r=50, t=40, b=20), yaxis_title=None,
                                    font=dict(size=14)
                                )
                                st.plotly_chart(fig_item, use_container_width=True)
                                st.markdown("---")
            st.divider()

            # D. Komparasi Antar Buku
            st.subheader("4. Perbandingan Komparatif Antar Buku")
            st.info("Pilih kategori di bawah ini untuk membandingkan distribusi antar buku secara berdampingan.")
            
            col_tools_1, col_tools_2 = st.columns([2, 1])
            with col_tools_1:
                comp_tinjauan = st.selectbox("Pilih Kategori:", tinjauan_cols, key="compare_select")
            with col_tools_2:
                mode_tampilan = st.radio("Mode Tampilan:", ["Grid Terpisah (Faceted)", "Berkelompok (Grouped)"], horizontal=True)
            
            if comp_tinjauan:
                df_comp = data_untuk_stats.dropna(subset=['Buku', comp_tinjauan])
                df_comp_agg = df_comp.groupby(['Buku', comp_tinjauan]).size().reset_index(name='Jumlah')
                
                list_item_urut = sorted(df_comp_agg[comp_tinjauan].unique())
                
                if not df_comp_agg.empty:
                    dynamic_height_comp = max(400, len(list_item_urut) * 40 + 100)
                    
                    # Sort Descending agar visual Ascending
                    df_comp_agg = df_comp_agg.sort_values(by=comp_tinjauan, ascending=False)
                    category_order_visual = list_item_urut[::-1]

                    if mode_tampilan == "Grid Terpisah (Faceted)":
                        fig_comp = px.bar(
                            df_comp_agg, y=comp_tinjauan, x="Jumlah", color="Buku", 
                            facet_col="Buku", 
                            title=f"Perbandingan: {comp_tinjauan} (Mode Grid)", text_auto=True,
                            category_orders={
                                comp_tinjauan: category_order_visual, 
                                "Buku": opsi_buku
                            }
                        )
                    else:
                        fig_comp = px.bar(
                            df_comp_agg, y=comp_tinjauan, x="Jumlah", color="Buku", barmode="group",
                            title=f"Perbandingan: {comp_tinjauan} (Mode Grouped)", text_auto=True,
                            category_orders={
                                comp_tinjauan: category_order_visual,
                                "Buku": opsi_buku
                            }
                        )
                    
                    fig_comp.update_traces(
                        textposition="outside", 
                        textfont=dict(size=16), 
                        cliponaxis=False
                    )
                    
                    fig_comp.update_layout(
                        height=dynamic_height_comp, 
                        yaxis_title=None, 
                        xaxis_title="Jumlah Soal", 
                        legend_title="Buku",
                        font=dict(size=14) 
                    )
                    
                    if mode_tampilan == "Grid Terpisah (Faceted)":
                        fig_comp.update_xaxes(matches=None, showticklabels=True)
                        
                    st.plotly_chart(fig_comp, use_container_width=True)
                else:
                    st.warning("Belum ada data untuk kategori ini.")

else:
    st.info("👋 Selamat Datang! Silakan klik **'📂 PANEL INPUT DATA'** di atas untuk mulai meng-upload file.")
