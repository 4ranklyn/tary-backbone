package com.example.tary.utils

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.PowerManager

/**
 * HealthMonitor bertugas memantau status fisik perangkat secara berkesinambungan
 * guna menentukan mode operasional Tary Engine (AI Chat vs Static Search).
 * Mode 'Crisis Mode' akan diaktifkan untuk menghemat daya ketika perangkat
 * kritis (baterai minim atau suhu membahayakan komponen lokal AI).
 */
class HealthMonitor(private val context: Context) {

    // Threshold crisis mode
    companion object {
        const val CRITICAL_BATTERY_LEVEL = 15 // persentase
    }

    // Enum representing the operational mode
    enum class EngineMode {
        AI_CHAT,        // Full RAG Pipeline: Vector Search + LLM Generation
        STATIC_SEARCH   // Fallback Pipeline: SQL Like/Full-text Search tanpa LLM
    }

    /**
     * Memeriksa kondisi sistem saat ini dan mengembalikan Mode Mesin yang direkomendasikan.
     */
    fun determineEngineMode(): EngineMode {
        val batterySufficient = isBatterySufficient()
        val thermalSafe = isThermalSafe()
        val isPowerSaveModeOn = isPowerSaveModeActivated()

        // Jika salah satu indikator menunjukkan krisis, langsung jatuh ke Static Search
        if (!batterySufficient || !thermalSafe || isPowerSaveModeOn) {
            triggerCrisisAlert(!batterySufficient, !thermalSafe)
            return EngineMode.STATIC_SEARCH
        }

        return EngineMode.AI_CHAT
    }

    /**
     * Mengecek persentase baterai.
     * Mengembalikan true jika baterai >= CRITICAL_BATTERY_LEVEL atau sedang di-charge.
     */
    private fun isBatterySufficient(): Boolean {
        val batteryStatus: Intent? = IntentFilter(Intent.ACTION_BATTERY_CHANGED).let { ifilter ->
            context.registerReceiver(null, ifilter)
        }

        val level: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        
        // Memeriksa status pengisian daya
        val status: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        val isCharging: Boolean = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                                  status == BatteryManager.BATTERY_STATUS_FULL

        if (level == -1 || scale == -1) return true // Gagal membaca baterai, asumsikan aman
        
        val batteryPct = level * 100 / scale.toFloat()
        
        // Jika sedang di charge, baterai selalu dianggap non-krisis
        if (isCharging) return true
        
        return batteryPct > CRITICAL_BATTERY_LEVEL
    }

    /**
     * Memeriksa status Thermal Throttling Android (API 29+).
     * Mencegah Local LLM membakar mesin jika suhu sudah kritis (Severe ke atas).
     */
    private fun isThermalSafe(): Boolean {
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        
        return if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            val thermalStatus = powerManager.currentThermalStatus
            // Jika Thermal berstatus SEVERE, CRITICAL, EMERGENCY, atau SHUTDOWN
            thermalStatus < PowerManager.THERMAL_STATUS_SEVERE
        } else {
            // Untuk Android versi lama, kita harus baca suhu diskriminatif manual
            // dari /sys/class/thermal/thermal_zone*/temp (Tidak disertakan di sini but asumsikan aman)
            true 
        }
    }

    /**
     * Memeriksa apakah user mengaktifkan "Battery Saver" / "Power Saving Mode" secara manual.
     */
    private fun isPowerSaveModeActivated(): Boolean {
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        return powerManager.isPowerSaveMode
    }

    /**
     * Fungsi opsional untuk memancarkan event peringatan ke UI (bisa menggunakan LiveData/Flow/EventBus).
     */
    private fun triggerCrisisAlert(batteryLow: Boolean, thermalHigh: Boolean) {
        // Contoh implementasi mencetak Alert ke Log/UI:
        val reason = mutableListOf<String>()
        if (batteryLow) reason.add("Baterai di bawah $CRITICAL_BATTERY_LEVEL%")
        if (thermalHigh) reason.add("Suhu perangkat terlampau tinggi")
        
        // Broadcast peringatan ke UI Layer (Activity/Fragment)
        // val message = "CRISIS MODE AKTIF: ${reason.joinToString(" & ")}. Beralih ke Pencarian Statis..."
        // _crisisModeEvent.postValue(message)
    }
}

// ==============================================================================
// CONTOH PEMANGGILAN DI DALAM VIEWMODEL / REPOSITORY (Pseudocode)
// ==============================================================================
/*
class SurvivalViewModel(
    private val healthMonitor: HealthMonitor,
    private val taryEngine: TaryEngineLocal,
    private val staticSearchRepo: StaticSearchRepository
) : ViewModel() {

    fun executeQuery(userQuery: String) {
        val currentMode = healthMonitor.determineEngineMode()
        
        if (currentMode == EngineMode.AI_CHAT) {
            // Eksekusi RAG lengkap (Embed -> Vector Search -> LLM Generate) lambat & rakus daya
            viewModelScope.launch {
                val context = taryEngine.retrieveContext(userQuery)
                val response = taryEngine.generateResponse(userQuery, context)
                _uiState.value = UIState.SuccessAI(response)
            }
        } else {
            // Crisis Mode (Fallback List Search) = Gak pake LLM, Gak Pake Embedding Model (ONNX).
            // Cuma nembak SQL 'LIKE %query%' ke Room dan tampilin teks mentah.
            viewModelScope.launch {
                val staticResults = staticSearchRepo.searchManualsByKeyword(userQuery)
                val responseMsg = "Mode Hemat Daya Aktif. Menampilkan hasil pencarian statis:\n\n$staticResults"
                _uiState.value = UIState.SuccessStatic(responseMsg)
            }
        }
    }
}
*/
