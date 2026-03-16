package com.example.tary.ai

import android.content.Context
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import java.io.File
import com.example.tary.data.local.ManualChunkDao
// import com.example.tary.data.local.VectorChunkBox // Asumsi ObjectBox

/**
 * LlamaEngineManager: Wrapper Kotlin untuk llama.cpp Android JNI
 * Kelas ini bertugas memuat file gemma3-1b-it-q4.gguf dari penyimpanan internal,
 * mengambil konteks RAG dari ObjectBox/Room, dan menggerakkan proses Chat (Inference).
 */
class LlamaEngineManager(
    private val context: Context,
    private val manualChunkDao: ManualChunkDao,
    // private val vectorBox: VectorChunkBox 
) {
    // Referensi ke C++ pointer llama_context
    private var llamaContextPtr: Long = 0

    // Dummy deklarasi JNI untuk JNI C++ Backend Llama.cpp
    private external fun loadModelJNI(modelPath: String, threads: Int, contextSize: Int): Long
    private external fun generateResponseJNI(contextPtr: Long, prompt: String, temperature: Float): String
    private external fun freeModelJNI(contextPtr: Long)

    init {
        // Load file .so library (C++ pre-compiled llama.cpp)
        // System.loadLibrary("llama-android")
    }

    /**
     * Pindahkan file .gguf dari folder assets Android ke internal storage
     * karena C++ JNI butuh absolute path dari file system.
     */
    fun initializeEngine() {
        val modelFilename = "gemma3-1b-it-q4.gguf"
        val modelFile = File(context.filesDir, modelFilename)

        if (!modelFile.exists()) {
            context.assets.open(modelFilename).use { input ->
                modelFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }

        // Konfigurasi performa HP: 4 utas CPU, 1024 Panjang Konteks
        llamaContextPtr = loadModelJNI(modelFile.absolutePath, threads = 4, contextSize = 1024)
    }

    /**
     * Mengalirkan respons layaknya Streaming dari Ollama, tetapi langsung di HP.
     */
    fun processRagAndGenerateStream(userMessage: String): Flow<String> = flow {
        if (llamaContextPtr == 0L) {
            emit("Error: Model Gemma belum dimuat di memori HP.")
            return@flow
        }

        // 1. Ekstrak Konteks Medis via RAG (Dummy Implementasi)
        val ragContext = retrieveRelevantContext(userMessage)

        // 2. Format Prompt Gemma
        val formattedPrompt = """
            <start_of_turn>user
            Konteks Medis: 
            ${ragContext}
            
            Jawab pertanyaan berikut secara singkat berdasarkan konteks: 
            $userMessage<end_of_turn>
            <start_of_turn>model
        """.trimIndent()

        // 3. Inference C++ (Stream by token) 
        // Realita JNI: Fungsi C++ akan mengirimkan callback per-token kembali ke Kotlin.
        // Di sini kita gunakan mock logic string.
        val finalAnswer = generateResponseJNI(llamaContextPtr, formattedPrompt, 0.3f)
        
        // Memecah menjadi aliran token untuk UI Jetpack Compose
        val tokens = finalAnswer.split(" ")
        for (token in tokens) {
            emit("$token ")
            kotlinx.coroutines.delay(50) // Simulasi kecepatan token C++
        }
    }

    private suspend fun retrieveRelevantContext(query: String): String {
        // [TODO]: 
        // 1. Panggil ONNX Model lokal: string -> FloatArray
        // val queryVector = onnxEngine.embed(query)
        
        // 2. Pencarian ObjectBox (Hnsw Nearest Neighbor)
        // val bestMatchId = vectorBox.query().nearestNeighbors(queryVector, 1).findFirst()?.id
        
        // 3. Ambil teks aktual dari SQLite/Room
        // val chunk = manualChunkDao.getChunkById(bestMatchId)
        // return chunk.contentText
        
        return "Gunakan air mengalir untuk mendinginkan luka bakar."
    }

    fun release() {
        if (llamaContextPtr != 0L) {
            freeModelJNI(llamaContextPtr)
            llamaContextPtr = 0L
        }
    }
}
