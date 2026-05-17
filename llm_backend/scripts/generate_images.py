"""通义万相批量生成产品图 — Apple 暗色风格"""
import os, time, json, requests

API_KEY = "sk-1cd7bb921357485d94b0d36aae7b496d"
BASE_URL = "https://dashscope.aliyuncs.com"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "product-images")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "X-DashScope-Async": "enable"}

PRODUCTS = [
    ("smartphone", "iPhone 16 Pro Max", "titanium gray finish, triple camera"),
    ("smartphone", "Huawei Mate 70 Pro", "obsidian black, circular camera module"),
    ("smartphone", "Xiaomi 15 Ultra", "white ceramic, large round camera"),
    ("smartphone", "Samsung Galaxy S25 Ultra", "titanium silver, quad camera array"),
    ("laptop", "MacBook Pro 16 M4", "space black, minimalist design"),
    ("laptop", "ThinkPad X1 Carbon", "matte black, red TrackPoint"),
    ("laptop", "ROG Zephyrus G16", "dark gray, angular gaming design"),
    ("laptop", "Huawei MateBook X Pro", "dark blue metallic, ultra-thin"),
    ("tablet", "iPad Pro M4 13-inch", "space black, edge-to-edge display"),
    ("tablet", "Huawei MatePad Pro 13.2", "white, narrow bezel"),
    ("tablet", "Xiaomi Pad 7 Pro", "dark gray, minimalist"),
    ("earbuds", "AirPods Pro 3", "white, open charging case"),
    ("earbuds", "Huawei FreeBuds Pro 4", "silver gray, matte finish"),
    ("headphones", "Sony WH-1000XM6", "black, over-ear, premium"),
    ("smartwatch", "Apple Watch Ultra 3", "titanium, orange action button"),
    ("smartwatch", "Huawei Watch GT 5 Pro", "titanium, classic crown"),
    ("smartwatch", "Xiaomi Watch S4", "black, sporty design"),
    ("charger", "Anker Prime 20W GaN Charger", "black, ultra-compact cube"),
    ("charger", "Xiaomi 120W GaN Charger", "white, dual-port"),
    ("charger", "Baseus 65W GaN Charger", "black, 2C1A ports"),
]

STYLE = ("product photography isolated on dark charcoal background nearly black, "
         "angled at 30 degrees, dramatic studio lighting, edge rim light highlighting contours, "
         "minimalist Apple style, premium e-commerce, hyper-detailed materials texture, "
         "4K, no text no hands no logos no watermarks")


def generate_image(prompt, index):
    body = {
        "model": "wanx2.0-t2i-turbo",
        "input": {"prompt": prompt},
        "parameters": {"size": "1024*1024", "n": 1},
    }
    r = requests.post(f"{BASE_URL}/api/v1/services/aigc/text2image/image-synthesis",
                      headers=HEADERS, json=body)
    task = r.json()
    task_id = task["output"]["task_id"]
    print(f"  [{index}] Task {task_id} submitted")

    # Poll
    for _ in range(30):
        time.sleep(3)
        r = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {API_KEY}"})
        result = r.json()
        status = result["output"]["task_status"]
        if status == "SUCCEEDED":
            url = result["output"]["results"][0]["url"]
            return url
        elif status == "FAILED":
            print(f"  [{index}] FAILED: {result}")
            return None
    print(f"  [{index}] TIMEOUT")
    return None


def download(url, filepath):
    r = requests.get(url)
    with open(filepath, "wb") as f:
        f.write(r.content)
    size = len(r.content)
    print(f"  -> {filepath} ({size // 1024}KB)")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Generating {len(PRODUCTS)} product images...\n")

    for i, (ptype, name, detail) in enumerate(PRODUCTS, 1):
        prompt = f"{STYLE}. {ptype}: {detail}"
        print(f"[{i}/{len(PRODUCTS)}] {name}")
        url = generate_image(prompt, i)
        if url:
            safe_name = name.lower().replace(" ", "-").replace('"', '').replace("'", "")
            filepath = os.path.join(OUTPUT_DIR, f"{safe_name}.png")
            download(url, filepath)
        time.sleep(1)

    print(f"\nDone. {len(os.listdir(OUTPUT_DIR))} images in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
