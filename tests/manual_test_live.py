import httpx
import sys

sys.stdout.reconfigure(encoding="utf-8")

base_url = "http://127.0.0.1:8005/api"

print("--- TEST 1: Greeting / Introduction (Georgian) ---")
r1 = httpx.post(
    f"{base_url}/chat",
    json={"message": "სალამი, ვინ ხარ შენ და რას აკეთებ ჩემს სასახლეში?"},
    timeout=120.0
)
assert r1.status_code == 200, f"Error: {r1.text}"
d1 = r1.json()
conv_id = d1["conversation_id"]
print(f"Conversation ID: {conv_id}")
print(f"Model: {d1.get('model')}")
print(f"JESTER Response:\n{d1['response']}\n")

# Check stage directions
has_stage_direction_1 = "*" in d1["response"] or "(იცინის)" in d1["response"] or "(laughs)" in d1["response"]
print(f"Stage directions detected: {has_stage_direction_1}")

print("\n--- TEST 2: Serious Technical Question (TCP vs UDP) ---")
r2 = httpx.post(
    f"{base_url}/chat",
    json={"conversation_id": conv_id, "message": "მითხარი, რა განსხვავებაა TCP და UDP პროტოკოლებს შორის? ზუსტი და ტექნიკური პასუხი მინდა."},
    timeout=120.0
)
assert r2.status_code == 200, f"Error: {r2.text}"
d2 = r2.json()
print(f"JESTER Response:\n{d2['response']}\n")

print("\n--- TEST 3: Memory / Context Continuity ---")
r3 = httpx.post(
    f"{base_url}/chat",
    json={"conversation_id": conv_id, "message": "გახსოვს, რა იყო პირველი შეკითხვა, რაც ამ საუბარში დაგისვი?"},
    timeout=120.0
)
assert r3.status_code == 200, f"Error: {r3.text}"
d3 = r3.json()
print(f"JESTER Response:\n{d3['response']}\n")

print("\n--- TEST 4: Ridiculous Idea (English) ---")
r4 = httpx.post(
    f"{base_url}/chat",
    json={"conversation_id": conv_id, "message": "I have decided to store all our production passwords in plaintext in a public GitHub repository to make backups easier. What do you think?"},
    timeout=120.0
)
assert r4.status_code == 200, f"Error: {r4.text}"
d4 = r4.json()
print(f"JESTER Response:\n{d4['response']}\n")

print("\n--- TEST 5: Verify Saved Conversation History ---")
r5 = httpx.get(f"{base_url}/conversations/{conv_id}")
d5 = r5.json()
print(f"Stored message count: {len(d5.get('messages', []))}")
assert len(d5.get("messages", [])) == 8, "Expected 4 user messages + 4 assistant responses"
print("Verification complete!")
