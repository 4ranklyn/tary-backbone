package com.example.tary.data.local

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
// import io.objectbox.annotation.Entity as ObjectBoxEntity
// import io.objectbox.annotation.Id as ObjectBoxId
// import io.objectbox.annotation.HnswIndex

/**
 * -------------------------------------------------------------
 * ROOM DATABASE SCHEMA (Relational Store)
 * -------------------------------------------------------------
 * Entity ini digunakan untuk menyimpan metadata dan teks aktual dari
 * potongan panduan survival (Chunks) di SQLite via Room Database.
 */
@Entity(tableName = "survival_manual_chunks")
data class ManualChunkEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    @ColumnInfo(name = "category_header")
    val categoryHeader: String,  // Contoh: "Bab 1. Luka > Luka Bakar"
    
    @ColumnInfo(name = "content_text")
    val contentText: String      // Teks panduan aktual
)

@Dao
interface ManualChunkDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertChunk(chunk: ManualChunkEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(chunks: List<ManualChunkEntity>): List<Long>

    @Query("SELECT * FROM survival_manual_chunks WHERE id = :chunkId")
    suspend fun getChunkById(chunkId: Long): ManualChunkEntity?

    @Query("SELECT COUNT(*) FROM survival_manual_chunks")
    suspend fun getCount(): Int
    
    @Query("DELETE FROM survival_manual_chunks")
    suspend fun deleteAll()
}

/**
 * -------------------------------------------------------------
 * OBJECTBOX VECTOR SEARCH SCHEMA (Vector Store)
 * -------------------------------------------------------------
 * Entity ini terpisah dan khusus untuk ObjectBox. 
 * ObjectBox digunakan untuk melakukan High-Dimensional Vector Search (HNSW)
 * karena SQLite/Room standar tidak mendukung tipe data FloatArray untuk cosine similarity.
 */
/*
@ObjectBoxEntity
data class VectorChunkEntity(
    @ObjectBoxId
    var id: Long = 0, // ID ini akan disinkronkan / dipetakan dengan ID di ManualChunkEntity (Room)
    
    // Anotasi HnswIndex menandakan kolom ini sebagai index pencarian vektor.
    // Dimensions disesuaikan dengan output embedding model Anda (misal all-MiniLM-L6-v2 = 384, Nomic = 768)
    @HnswIndex(dimensions = 384)
    var embeddingVector: FloatArray? = null
)
*/

/**
 * Contoh Flow Sistem (Repository Pattern) yang akan terjadi di Android:
 * 
 * 1. User mengetik "Panas luka wajan"
 * 2. Lokal ONNX Runtime mengubah string menjadi `floatArrayOf(...)` (Embeddings)
 * 3. ObjectBox mencari `VectorChunkEntity` terdekat menggunakan HnswIndex (nearest neighbors)
 * 4. ObjectBox mengembalikan list ID terbaik (misal: ID 45 dan 89)
 * 5. Aplikasi melakukan Query ke Room DB: `dao.getChunkById(45)` untuk mendapatkan Teks Aktual dan Metadata
 * 6. Teks aktual digabungkan dengan Prompt dan dikirim ke Ollama/Gemma (Macaque) lokal
 */
