import time

class Profiler:
    def __init__(self):
        self.metrics = {}
        self.start_times = {}

    def tick(self, name):
        """Mulai mencatat stopwatch untuk suatu proses."""
        self.start_times[name] = time.time()

    def tock(self, name):
        """Hentikan stopwatch dan simpan selisih waktu (dalam detik)."""
        if name in self.start_times:
            elapsed = time.time() - self.start_times[name]
            self.metrics[name] = elapsed
            return elapsed
        return 0.0
        
    def set(self, name, value):
        """Set nilai metrik secara manual secara spesifik (misal kecepatan token/s)."""
        self.metrics[name] = value

    def print_report(self):
        """Tampilkan hasil profiling ke terminal dalam format tabel."""
        print("\n" + "="*55)
        print(" ⏱️  TARY ENGINE PROFILING METRICS")
        print("="*55)
        print(f"| {'Metrik':<28} | {'Nilai':<20} |")
        print("-" * 55)
        
        rt = self.metrics.get("retrieval_time", 0.0)
        ttft = self.metrics.get("ttft", 0.0)
        tps = self.metrics.get("tokens_per_sec", 0.0)
        
        print(f"| {'Retrieval Time (Chroma)':<28} | {rt:.4f} detik{' ':>8} |")
        print(f"| {'Time To First Token (TTFT)':<28} | {ttft:.4f} detik{' ':>8} |")
        print(f"| {'Tokens Per Second (Speed)':<28} | {tps:.2f} tokens/s{' ':>6} |")
        print("="*55 + "\n")

# Singleton intance yang bisa dipanggil global
rag_profiler = Profiler()
