import os
from rag_test import TaryEngine

def print_menu():
    print("\n" + "="*50)
    print("🛠️  TARY SURVIVAL ENGINE - MAINTENANCE TOOLS 🛠️")
    print("="*50)
    print("1. Lihat Statistik Database (Jumlah Chunk)")
    print("2. Tampilkan 5 Chunk Pertama")
    print("3. Cari Chunk Spesifik berdasarkan Kata Kunci")
    print("4. Hapus Chunk Berdasarkan ID")
    print("5. Reset/Hapus Seluruh Database (DANGER)")
    print("0. Keluar")
    print("="*50)

def main():
    print("Menginisialisasi Mesin Tary...")
    engine = TaryEngine()
    
    if not engine.vectorstore:
        print("❌ Error: TaryEngine gagal memuat ChromaDB. Pastikan folder chroma_db/ sudah ada.")
        return
        
    collection = engine.vectorstore._collection
    
    while True:
        print_menu()
        choice = input("Pilih menu (0-5): ")
        
        if choice == '0':
            print("Keluar dari program maintenance.")
            break
            
        elif choice == '1':
            count = collection.count()
            print(f"\n📊 Statistik Database:")
            print(f"Total Chunk Teks Tersimpan: {count}")
            print(f"Directory Penyimpanan: {engine.persist_directory}")
            
        elif choice == '2':
            # Mengambil maksimal 5 data pertama dari database
            results = collection.get(limit=5)
            ids = results['ids']
            documents = results['documents']
            metadatas = results['metadatas']
            
            print(f"\n📑 Menampilkan {len(ids)} Chunk Pertama:")
            for i in range(len(ids)):
                print(f"\n--- [ID: {ids[i]}] ---")
                
                # Format Metadata
                meta_str = " > ".join(metadatas[i].values()) if metadatas[i] else "Tanpa Metadata"
                print(f"Header     : {meta_str}")
                
                # Truncate string panjang
                doc_preview = documents[i].replace('\n', ' ')[:100] + "..."
                print(f"Isi Potongan : {doc_preview}")
                
        elif choice == '3':
            keyword = input("\nMasukkan kata kunci pencarian (teks): ")
            print(f"Mencari dokumen yang mengandung: '{keyword}'...")
            
            # Bisa ditambahkan where_document({"$contains":"keyword"}) di ChromaDB versi lebih baru
            # Di sini kita fallback dengan pencarian teks basic ambil data 100 teratas saja lalu filter python
            results = collection.get() 
            ids = results['ids']
            documents = results['documents']
            
            found = 0
            for i in range(len(documents)):
                if keyword.lower() in documents[i].lower():
                    found += 1
                    print(f"\n[ID: {ids[i]}]")
                    meta_str = " > ".join(results['metadatas'][i].values()) if results['metadatas'][i] else "No Meta"
                    print(f"Kategori : {meta_str}")
                    print(f"Preview  : {documents[i][:100]}...\n")
                    
            print(f"Total ditemukan: {found} dokumen.")
            
        elif choice == '4':
            target_id = input("\nMasukkan ID Chunk yang ingin dihapus: ")
            
            # Verifikasi apakah ID tersebut ada
            check = collection.get(ids=[target_id])
            if not check['ids']:
                print(f"❌ Dokumen dengan ID '{target_id}' tidak ditemukan.")
            else:
                confirm = input(f"Yakin ingin menghapus dokumen ID '{target_id}'? (y/n): ")
                if confirm.lower() == 'y':
                    collection.delete(ids=[target_id])
                    print(f"✅ Dokumen ID '{target_id}' berhasil dihapus dari vector database.")
                    
        elif choice == '5':
            confirm1 = input("\n⚠️ PERINGATAN: Anda akan menghapus SELURUH vector database.\nKetik 'HAPUS' untuk melanjutkan: ")
            if confirm1 == 'HAPUS':
                 print("Menyekrup ulang database...")
                 import shutil
                 # Hapus dari memori Chroma Local
                 try:
                     # Delete underlying directory physically
                     if os.path.exists(engine.persist_directory):
                         shutil.rmtree(engine.persist_directory)
                     print("✅ Seluruh Database dan Folder chroma_db berhasil di-reset.")
                     print("Anda harus meng-ingest ulang manual text selanjutnya.")
                     break # Paksa keluar karena objek engine sudah tidak valid
                 except Exception as e:
                     print(f"Gagal mereset database: {e}")
            else:
                 print("Proses reset dibatalkan.")
                 
        else:
            print("Pilihan tidak valid.")

if __name__ == "__main__":
    main()
