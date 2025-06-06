from openai import OpenAI

import requests
import os
import csv
import json
from datetime import datetime
from time import sleep
import argparse
from fetch_trending_topics_free import get_combined_trending_topics

# CONFIGURATION
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OPENAI_HEADERS = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
NUM_IMAGES = 20
IMAGE_OUTPUT_DIR = "dalle_images"
USAGE_LOG_FILE = "dalle_usage_log.csv"
CSV_FILE = "metadata.csv"
IMAGE_COSTS = {
    "1024x1024": 0.04,
    "1024x1792": 0.08,
    "1792x1024": 0.08
}




# Ensure output directory exists
os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


def load_quotes_from_csv(csv_file, max_quotes=20):
    quotes = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'quote' in row and row['quote'].strip():
                    quotes.append(row['quote'].strip())
                if len(quotes) >= max_quotes:
                    break
    except Exception as e:
        print(f"⚠️ Error reading quotes CSV: {e}")
    return quotes

def quote_to_prompt(quote):
    return f"A stylized vector design inspired by the Stoic quote: {quote}"

def save_prompts_to_csv(prompts, output_dir=".", prefix="prompts"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{prefix}_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["prompt"])
            for prompt in prompts:
                writer.writerow([prompt])
        print(f"📄 Saved prompts to: {filepath}")
        return filepath
    except Exception as e:
        print(f"⚠️ Failed to save prompts CSV: {e}")
        return None

# STEP 2: Use ChatGPT to generate 20 image prompts
def generate_prompts_from_topics(topics):
    topic_list = "\n".join(f"- {topic}" for topic in topics)
    prompt = (
        f"Today is {datetime.now().strftime('%B %d, %Y')}.\n"
        f"Here are some trending topics:\n{topic_list}\n\n"
        f"Based on these, generate 20 short and imaginative image design prompts for DALL·E. "
        f"Each should be a single sentence or phrase describing a visually interesting vector image for a T-Shirt. Format as a numbered list."
    )

    response = client.chat.completions.create(model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a creative design assistant for a hip clothing company."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.9)

    return response.choices[0].message.content

# STEP 3: Extract and clean up prompts
def extract_prompts(text):
    lines = text.strip().split("\n")
    prompts = [line.split(".", 1)[1].strip() for line in lines if "." in line]
    return prompts[:NUM_IMAGES]

# --- Log Usage ---
def log_image_usage(prompt, size="1024x1024", filepath=None):
    cost = IMAGE_COSTS.get(size, 0.04)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "timestamp": timestamp,
        "prompt": prompt,
        "size": size,
        "filepath": filepath or "",
        "cost_usd": f"{cost:.2f}"
    }
    try:
        file_exists = os.path.isfile(USAGE_LOG_FILE)
        with open(USAGE_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        print(f"⚠️ Error logging image usage: {e}")


# Generate images using DALL·E (OpenAI Image API)
def generate_image(prompt, index, size="1024x1024"):
    try:
        #model="dall-e-2", if wanting lower cost
        response = client.images.generate(prompt=prompt,
        model="dall-e-3",
        n=1,
        size=size)
        image_url = response.data[0].url
        print(f"Image {index+1}: {prompt} -> {image_url}")

        # Download image
        img_data = requests.get(image_url).content
        timestamp = datetime.now().strftime("%Y-%b-%d_%H%M")
        filename = os.path.join(IMAGE_OUTPUT_DIR, f"dalle_image_{index+1}_{timestamp}.png")
        with open(filename, "wb") as f:
            f.write(img_data)

        log_image_usage(prompt, size=size, filepath=filename)
        return filename
    except Exception as e:
        print(f"❌ Error generating image for prompt {index+1}: {e}")
        return None


def write_metadata_to_csv(records, csv_file):
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Index", "Prompt", "FilePath"])
        for i, (prompt, filepath) in enumerate(records):
            writer.writerow([i + 1, prompt, filepath])


# MAIN
if __name__ == "__main__":
    # Parse CLI args
    parser = argparse.ArgumentParser(description="Generate daily DALL·E image designs from trending topics.")
    parser.add_argument("--dry-run", action="store_true", help="Only generate and preview prompts, do not call DALL·E.")
    parser.add_argument("--quote-csv", help="Path to a CSV file with a 'quote' column to also generate image prompts.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES, help="Maximum number of images to generate (default: 20).")
    args = parser.parse_args()

    prompts = []

    # Optional: also load quote prompts
    if args.quote_csv:
        quote_texts = load_quotes_from_csv(args.quote_csv)
        prompts = [quote_to_prompt(q) for q in quote_texts]
        #quote_prompts = [quote_to_prompt(q) for q in quote_texts]
        #prompts.extend(quote_prompts)
    else:
        # Get trending topics and generate prompts
        topics = get_combined_trending_topics()
        prompt_texts = generate_prompts_from_topics(topics)
        prompts = extract_prompts(prompt_texts)

    if not prompts:
        print("⚠️ No prompts to generate images from. Exiting.")
        exit(0)

    # Limit prompts to max_images
    prompts = prompts[:args.max_images]

    # Save intermediate CSV to review later
    save_prompts_to_csv(prompts, output_dir=".")

    # Dry-run break
    if args.dry_run:
        print("\n🛑 Dry-run mode active. No images were generated.\n")
        exit(0)

    # Generate images and save metadata
    print(f"\n🎨 Generating {len(prompts)} DALL·E images...\n")
    metadata_records = []

    for i, prompt in enumerate(prompts):
        filepath = generate_image(prompt, i)
        if filepath:
            metadata_records.append((prompt, filepath))
        sleep(2)  # Stay within rate limits

    write_metadata_to_csv(metadata_records, CSV_FILE)
    print(f"\n✅ All images generated and metadata saved to: {CSV_FILE}")