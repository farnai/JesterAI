import json
import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app import app

PROMPTS = [
    ("A", "დღეს ძალიან ცუდ ხასიათზე ვარ და საერთოდ არ ვიცი რა გავაკეთო."),
    ("B", "ამიხსენი მარტივად რა განსხვავებაა TCP-სა და UDP-ს შორის."),
    ("C", "მომიფიქრე იდეა პატარა ბიზნესისთვის საქართველოში."),
    ("D", "მე მგონია, რომ პაროლების plaintext-ად GitHub-ზე შენახვა პრობლემა არ არის. რას იტყვი?"),
    ("E", "მოდი ვიკამათოთ. რატომ არის ხელოვნური ინტელექტის აგენტის აშენება საერთოდ საჭირო?"),
    ("F", "რა არის binary search და როგორ მუშაობს?"),
]

def run_live_inference():
    print("==================================================")
    print("  JESTER v0.2 — LIVE CANONICAL GEORGIAN BENCHMARK")
    print("  Model: qwen3.6:latest via Ollama")
    print("==================================================")
    
    client = TestClient(app)
    results = []

    # First verify health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Health check failed: {res_health.text}"
    health_data = res_health.json()
    print(f"Health check: provider={health_data['provider']}, model={health_data['model']}, status={health_data['status']}", flush=True)

    for idx, (label, prompt_text) in enumerate(PROMPTS, 1):
        user_id = f"usr_benchmark_{label.lower()}"
        print(f"\n[{idx}/6] Prompt {label}: {prompt_text}", flush=True)
        start_t = time.perf_counter()
        
        payload = {
            "user_id": user_id,
            "message": prompt_text,
        }
        
        res = client.post("/api/chat", json=payload)
        elapsed = round(time.perf_counter() - start_t, 2)
        
        if res.status_code != 200:
            print(f"  FAILED: HTTP {res.status_code} - {res.text}", flush=True)
            results.append({
                "prompt_id": label,
                "prompt": prompt_text,
                "status": res.status_code,
                "error": res.text,
                "latency_s": elapsed,
            })
            continue

        data = res.json()
        response_text = data["response"]
        print(f"  Latency: {elapsed}s | Tokens: prompt={data['usage'].get('prompt_tokens')}, comp={data['usage'].get('completion_tokens')}", flush=True)
        print(f"  Response:\n{response_text}\n", flush=True)
        
        # Check for banned stage directions
        banned_detected = []
        for marker in ["*(", ")*", "*", "(იცინის)", "(ოხრავს)", "(თავს ხრის)", "[იცინის]", "[თავს ხრის]"]:
            if marker in response_text:
                banned_detected.append(marker)

        results.append({
            "prompt_id": label,
            "prompt": prompt_text,
            "status": 200,
            "response": response_text,
            "latency_s": elapsed,
            "model": data["model"],
            "provider": data["provider"],
            "banned_markers_detected": banned_detected,
        })

    # Save results to disk
    output_path = PROJECT_ROOT / "tests" / "benchmark_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nBenchmark completed. Results saved to: {output_path}", flush=True)

if __name__ == "__main__":
    run_live_inference()
