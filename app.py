import streamlit as st
import os
import tempfile
from rag_test import TaryEngine

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    page_title="Tary Survival Engine",
    page_icon="🏕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Inisialisasi TaryEngine di Session State ---
# Memastikan TaryEngine hanya di-load sekali selama sesi
@st.cache_resource
def load_engine():
    return TaryEngine()

engine = load_engine()

# --- Inisialisasi Variabel Session State lainnya ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- CSS Tambahan untuk Styling Error/Warning ---
st.markdown("""
<style>
.safety-warning {
    background-color: #ffcccc;
    border-left: 6px solid #ff0000;
    color: #cc0000;
    padding: 10px 15px;
    margin-bottom: 20px;
    font-weight: bold;
    border-radius: 4px;
}
.source-box {
    background-color: #f0f2f6;
    border-radius: 5px;
    padding: 10px;
    margin-top: 10px;
    font-size: 0.85em;
    color: #555;
    border-left: 3px solid #0066cc;
}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: Upload Dokumen Tambahan ---
with st.sidebar:
    st.title("⚙️ Pengaturan Tary")
    st.markdown("Unggah file Markdown (.md) tambahan untuk memperkaya basis pengetahuan Survival / Medis.")
    
    uploaded_file = st.file_uploader("Upload Dokumen Baru", type=["md"])
    
    if uploaded_file is not None:
        if st.button("Proses Dokumen"):
            with st.spinner("Meng-ingest dokumen ke dalam vektor database..."):
                try:
                    # Simpan sementara file yang diunggah untuk dibaca oleh TaryEngine
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode='wb') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # Panggil ingest_manual dari TaryEngine
                    engine.ingest_manual(tmp_file_path)
                    
                    st.success(f"Berhasil memproses: {uploaded_file.name}")
                    
                    # Hapus file sementara
                    os.remove(tmp_file_path)
                except Exception as e:
                    st.error(f"Gagal memproses dokumen: {str(e)}")
                    
    st.divider()
    st.markdown("### Status Sistem")
    st.success("Tary:1B Engine Siap")
    st.success("ChromaDB Aktif")

# --- AREA UTAMA: Chat Interface ---
st.title("🏕️ Tary Survival Assistant")
st.markdown("Tanyakan seputar panduan pertolongan pertama atau survival di alam liar.")

# Menampilkan histori percakapan
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Jika ada sumber rujukan (metadata & potongan teks)
        if "source_metadata" in message and message["source_metadata"]:
            with st.expander("Lihat Sumber Referensi"):
                st.markdown(f"**Bab/Kategori:** `{' > '.join(message['source_metadata'].values())}`")
                st.markdown("👉 **Potongan Teks Asli:**")
                st.markdown(f"<div class='source-box'>{message['source_context']}</div>", unsafe_allow_html=True)

# --- INPUT USER ---
if prompt := st.chat_input("Contoh: Bagaimana cara membuat api unggun?"):
    # 1. Tampilkan input user
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Simpan input ke histori
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 3. Proses Jawaban
    with st.chat_message("assistant"):
        # Placeholder untuk warning safety
        warning_placeholder = st.empty()
        
        # Placeholder untuk teks jawaban LLM
        response_placeholder = st.empty()
        
        # --- Eksekusi TaryEngine ---
        with st.spinner("Berpikir (mengakses basis pengetahuan)..."):
            # a. Cek Safety Filter
            is_dangerous = engine.safety_filter(prompt)
            if is_dangerous:
                warning_msg = """
                <div class='safety-warning'>
                    Terdeteksi pertanyaan tentang penggunaan bahan berbahaya (misal: odol/mentega) pada luka bakar.<br>
                    <strong>JANGAN PERNAH</strong> mengoleskan bahan tersebut karena dapat menjebak panas dan memicu infeksi!<br>
                    Bilas dengan air mengalir bersuhu ruang selama 10-20 menit.
                </div>
                """
                warning_placeholder.markdown(warning_msg, unsafe_allow_html=True)
            
            # b. Retrieve Context
            context_found, metadata_found = engine.retrieve_context(prompt)
            
            # c. Generate Response via LLM
            # answer sekarang adalah sebuah generator
            answer_generator = engine.generate_response(prompt, context_found)
            
            # d. Tampilkan Jawaban Utama secara streaming
            import types
            if isinstance(answer_generator, types.GeneratorType):
                answer = st.write_stream(answer_generator)
            else:
                st.markdown(answer_generator)
                answer = answer_generator
            
            # e. Tampilkan Source Traceability Streamlit UI
            if metadata_found:
                with st.expander("Lihat Sumber Referensi"):
                    st.markdown(f"**Bab/Kategori:** `{' > '.join(metadata_found.values())}`")
                    st.markdown("👉 **Potongan Teks Asli:**")
                    st.markdown(f"<div class='source-box'>{context_found}</div>", unsafe_allow_html=True)
            
            # 4. Simpan jawaban ke histori (termasuk metadata sumber)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": answer,
                "source_metadata": metadata_found,
                "source_context": context_found
            })
