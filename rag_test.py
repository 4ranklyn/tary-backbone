import os
import json
import time
import requests
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from profiler import rag_profiler

class TaryEngine:
    def __init__(self, persist_directory="./chroma_db", collection_name="survival_manual"):
        # Menggunakan embedding ringan untuk RAG
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.vectorstore = None
        self.retriever = None
        
        # Coba load database saat inisialisasi jika foldernya ada
        self._initialize_db()

    def _initialize_db(self):
        """Memuat ChromaDB dari disk jika sudah ada"""
        if os.path.exists(self.persist_directory):
            print("Memuat ChromaDB dari direktori lokal...")
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                persist_directory=self.persist_directory, 
                embedding_function=self.embeddings
            )
            # Jika collection sudah ada isinya, kita langsung buat retriever-nya
            try:
                if self.vectorstore._collection.count() > 0:
                    self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 1})
                    print(f"Berhasil memuat {self.vectorstore._collection.count()} chunk dari disk.")
            except Exception as e:
                print(f"Info: {str(e)}")

    def ingest_manual(self, file_path):
        """
        Menggunakan MarkdownHeaderTextSplitter untuk memproses dokumen survival
        dan menyimpannya ke dalam ChromaDB.
        """
        print(f"Membaca dokumen: {file_path} ...")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_document = f.read()
        except FileNotFoundError:
            print(f"Error: File {file_path} tidak ditemukan.")
            return

        # Mendefinisikan header markdown yang akan dijadikan acuan pemisahan
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(markdown_document)
        
        print("Menyimpan chunk ke vektor database Chroma...")
        
        # Inisialisasi collection secara eksplisit dan simpan ke disk
        if not self.vectorstore:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            
        # Gunakan add_documents untuk menambah data ke koleksi yang sudah ada (tidak menimpa full database)
        self.vectorstore.add_documents(documents=md_header_splits)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 1})
        print(f"Proses ingestion {len(md_header_splits)} chunk selesai dan tersimpan di {self.persist_directory}.")

    def retrieve_context(self, query):
        """
        Mencari chunk paling relevan dari ChromaDB berdasarkan query.
        Mengembalikan tuple: (context_text, metadata_dict)
        """
        if not self.retriever:
            # Jika belum terinisialisasi, coba init lg
            self._initialize_db()
            
            # Jika tetap nggak ada (database kosong), kembalikan default
            if not self.retriever:
                return "Basis pengetahuan belum dimuat. Silakan Ingest data manual terlebih dahulu.", {}
            
        print(f"Mencari konteks relevan untuk query: '{query}'")
        rag_profiler.tick("retrieval_time")
        retrieved_docs = self.retriever.invoke(query)
        rag_profiler.tock("retrieval_time")
        
        if retrieved_docs:
            doc = retrieved_docs[0]
            # Karena kita menggunakan MarkdownHeaderTextSplitter, 
            # metadata akan berisi hirarki header tempat chunk tersebut berada
            return doc.page_content, doc.metadata
        return "Informasi tidak tersedia di panduan.", {}

    def safety_filter(self, query):
        """
        Safety Filter sederhana yang memberikan peringatan merah jika user
        bertanya tentang penggunaan bahan berbahaya pada luka bakar.
        """
        query_lower = query.lower()
        
        # Kata kunci yang sering disalahartikan untuk luka bakar
        dangerous_burn_remedies = ["odol", "pasta gigi", "mentega", "kecap", "kopi", "minyak", "es batu"]
        
        # Deteksi konteks luka bakar (bisa diperluas ke konteks medis lain secara spesifik)
        if "luka bakar" in query_lower or "panas" in query_lower or "melepuh" in query_lower or "terbakar" in query_lower:
            for remedy in dangerous_burn_remedies:
                if remedy in query_lower:
                    print(f"\n\033[91m[PERINGATAN KESELAMATAN]\033[0m")
                    print(f"\033[91mTerdeteksi penyebutan '{remedy}' pada konteks luka bakar/panas.\033[0m")
                    print("\033[91mJANGAN PERNAH mengoleskan bahan tersebut pada luka karena dapat menjebak panas dan menyebabkan infeksi parah!\033[0m")
                    print("\033[91mHanya gunakan air mengalir bersuhu ruang selama 10-20 menit untuk mendinginkan area.\033[0m")
                    print("-" * 50)
                    return True # Mengindikasikan filter ter-trigger (opsional jika ingin mengubah path logika LLM)
        
        return False

    def generate_response(self, query, context):
        """
        Melakukan POST request ke API Ollama lokal (tary:1b).
        Terdapat penanganan error jika Ollama belum berjalan atau status code bukan 200.
        """
        # Prompt yang diformat agar model fokus menjawab berdasarkan konteks
        prompt = f"Konteks Medis:\n{context}\n\nPertanyaan: {query}\n\nJawablah dengan bahasa Indonesia yang jelas berdasarkan konteks medis di atas."
        
        payload = {
            "model": "gemma3:1b",
            "prompt": prompt,
            "system": "Anda adalah asisten medis yang memberikan jawaban yang sangat singkat, padat, dan langsung ke intinya. Jangan mengulang konteks atau mengulang pertanyaan.",
            "stream": True, # Diaktifkan untuk mengukur Time to First Token dan Tokens/Sec
            "options": {
                "stop": ["\n\nLuka\n\n", "Penyebab:", "Gejala:", "Pengobatan:"],
                "temperature": 0.3, # Menurunkan temperature agar jawaban lebih deterministik
                "repeat_penalty": 1.2, # Menambahkan penalti agar model tidak mengulang kata yang sama
                "top_k": 40,
                "top_p": 0.9
            }
        }
        
        url = "http://localhost:11434/api/generate"
        
        try:
            rag_profiler.tick("ttft") # Mulai hitung stopwatch TTFT
            response = requests.post(url, json=payload, stream=True, timeout=120)
            
            # Cek status code, jika bukan 200 beri penanganan error
            if response.status_code == 200:
                first_token_received = False
                gen_start_time = 0.0
                token_count = 0
                
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        
                        # Deteksi saat token pertama mendarat
                        if not first_token_received:
                            rag_profiler.tock("ttft")
                            first_token_received = True
                            # Mulai stopwatch untuk hitung kecepatan pasca-token pertama
                            gen_start_time = time.time() 
                            
                        # Yield token ke frontend Streamlit
                        token = chunk.get('response', '')
                        yield token
                        token_count += 1
                        
                        # Ambil metrik Tokens per second pas udah selesai streamnya
                        if chunk.get('done'):
                            eval_count = chunk.get('eval_count', token_count)
                            total_gen_time = time.time() - gen_start_time
                            tps = eval_count / total_gen_time if total_gen_time > 0 else 0.0
                            rag_profiler.set("tokens_per_sec", tps)
                            break
                            
            else:
                yield f"[Error] Ollama API merespons dengan status code {response.status_code}. Detail: {response.text}"
                
        except requests.exceptions.ConnectionError:
            yield "[Error Koneksi] Gagal terhubung ke Ollama. Pastikan aplikasi Ollama lokal sudah berjalan."
        except requests.exceptions.Timeout:
            yield "[Error Timeout] Permintaan ke Ollama memakan waktu terlalu lama."
        except Exception as e:
            yield f"[Error Sistem] Terjadi kesalahan tak terduga: {str(e)}"

# ==========================================
# C O N T O H   P E N G G U N A A N
# ==========================================
if __name__ == "__main__":
    engine = TaryEngine()
    
    # 1. Ingest Data (Jalankan ini sekali saat pertama kali atau jika panduan diupdate)
    # Pastikan file tary_survival_manual.md ada di dalam folder!
    # engine.ingest_manual("tary_survival_manual.md")
    
    # 2. Simulasi Pertanyaan
    test_query = "Teman saya kena wajan panas, bolehkah saya oleskan odol ke lukanya?"
    print(f"\nPertanyaan User: {test_query}")
    
    # 2.5 Safety Filter Check
    engine.safety_filter(test_query)
    
    # 3. Retrieve Context (Sekarang mengembalikan teks dan metadatanya)
    context_found, metadata_found = engine.retrieve_context(test_query)
    
    print("\n--- KONTEKS DITEMUKAN ---")
    print(context_found)
    
    print("\n--- SUMBER INFORMASI ---")
    if metadata_found:
        print("Referensi dari:")
        for key, value in metadata_found.items():
            print(f"- {key}: {value}")
    else:
        print("Sumber tidak spesifik atau informasi tidak ditemukan.")
    
    # 4. Generate Response dari Model
    print("\nMemproses jawaban via Tary:1B (Ollama lokal)...\n")
    answer = engine.generate_response(test_query, context_found)
    
    print("--- JAWABAN TARY ENGINE ---")
    print(answer)
    
    # (Opsional) Tempelkan sumber pada jawaban akhir agar user langsung melihatnya
    if metadata_found:
        sumber = " > ".join(metadata_found.values())
        print(f"\n(\033[92mSumber Rujukan\033[0m: {sumber})")

    # Cetak Metrik Profiling
    rag_profiler.print_report()