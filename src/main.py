import os
import time
import redis
from redis.commands.search.field import TextField, VectorField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from datasets import load_dataset
import numpy as np
import json
from openai import OpenAI

# OpenAI API キーの設定
openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Redis接続（環境変数から接続情報を取得）
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
r = redis.Redis(host=redis_host, port=redis_port, db=0)

# RediSearchインデックスの設定
index_name = "airbnb-index"
schema = (
    TextField("name"),
    TextField("space"),
    TextField("description"),
    NumericField("price"),
    NumericField("accommodates"),
    TextField("amenities"),
    VectorField(
        "text_embedding",
        "FLAT",
        {
            "TYPE": "FLOAT32",
            "DIM": 1536,
            "DISTANCE_METRIC": "COSINE",
        },
    ),
    VectorField(
        "text_embedding_hnsw",
        "HNSW",
        {
            "TYPE": "FLOAT32",
            "DIM": 1536,
            "DISTANCE_METRIC": "COSINE",
            "M": 40,
            "EF_CONSTRUCTION": 200,
        },
    ),
    VectorField(
        "image_embedding",
        "FLAT",
        {
            "TYPE": "FLOAT32",
            "DIM": 512,
            "DISTANCE_METRIC": "COSINE",
        },
    ),
)


def setup_index():
    try:
        r.ft(index_name).create_index(
            fields=schema,
            definition=IndexDefinition(prefix=["airbnb:"], index_type=IndexType.HASH),
        )
    except redis.exceptions.ResponseError:
        # インデックスが既に存在する場合は無視
        pass


def check_data_loaded():
    return r.dbsize() > 0


def load_data():
    if check_data_loaded():
        print("Data already loaded. Skipping data loading.")
        return

    dataset = load_dataset("MongoDB/airbnb_embeddings", split="train")

    for i, item in enumerate(dataset):
        key = f"airbnb:{item['_id']}"

        # 価格の処理
        price = item["price"]
        if isinstance(price, str):
            price = int(price.strip("$").replace(",", ""))
        else:
            price = int(price)

        # amenitiesの処理
        amenities = item.get("amenities", [])
        if isinstance(amenities, list):
            amenities = json.dumps(amenities)

        data = {
            "name": item["name"],
            "space": item.get("space", ""),
            "description": item["description"],
            "price": price,
            "accommodates": item["accommodates"],
            "amenities": amenities,
            "text_embedding": np.array(item["text_embeddings"])
            .astype(np.float32)
            .tobytes(),
            "text_embedding_hnsw": np.array(item["text_embeddings"])
            .astype(np.float32)
            .tobytes(),
            "image_embedding": np.array(item["image_embeddings"])
            .astype(np.float32)
            .tobytes(),
        }

        r.hset(key, mapping=data)

        if i % 100 == 0:
            print(f"Loaded {i} items...")

    print(f"Data insertion complete. {len(dataset)} items loaded.")


def get_embedding(text):
    text = text.replace("\n", " ")
    response = openai_client.embeddings.create(
        input=[text], model="text-embedding-3-small"
    )
    return np.array(response.data[0].embedding)


def search_listings(
    query_embedding, top_k=5, min_price=0, max_price=1000, wifi_required=False
):
    query_vector = query_embedding.astype(np.float32).tobytes()

    # プレフィルタリング: 価格範囲
    price_filter = f"@price:[{min_price} {max_price}]"

    # FLAT検索クエリ
    print("\n=== FLAT Search ===")
    flat_start_time = time.time()

    flat_vector_query = f"({price_filter})=>[KNN {top_k * 2} @text_embedding $query_vector AS flat_score]"
    flat_q = Query(flat_vector_query).sort_by("flat_score").dialect(2)
    flat_results = r.ft(index_name).search(
        flat_q, query_params={"query_vector": query_vector}
    )

    flat_search_time = time.time() - flat_start_time
    print(f"Search Time: {flat_search_time:.4f} seconds")
    display_results(flat_results, "flat_score", top_k, wifi_required)

    # HNSW検索クエリ
    print("\n=== HNSW Search ===")
    hnsw_start_time = time.time()

    hnsw_vector_query = f"({price_filter})=>[KNN {top_k * 2} @text_embedding_hnsw $query_vector AS hnsw_score]"
    hnsw_q = Query(hnsw_vector_query).sort_by("hnsw_score").dialect(2)
    hnsw_results = r.ft(index_name).search(
        hnsw_q, query_params={"query_vector": query_vector}
    )

    hnsw_search_time = time.time() - hnsw_start_time
    print(f"Search Time: {hnsw_search_time:.4f} seconds")
    display_results(hnsw_results, "hnsw_score", top_k, wifi_required)

    # 検索時間の比較
    print("\n=== Performance Comparison ===")
    print(f"FLAT Search Time:  {flat_search_time:.4f} seconds")
    print(f"HNSW Search Time:  {hnsw_search_time:.4f} seconds")
    print(
        f"Speed Difference:  {(flat_search_time/hnsw_search_time):.2f}x faster with HNSW"
    )


def display_results(results, score_attr, top_k, wifi_required):
    displayed_results = 0

    for doc in results.docs:
        try:
            amenities_list = json.loads(doc.amenities)

            if wifi_required and "Wifi" not in amenities_list:
                continue

            print("\n" + "=" * 80)
            print(f"\nID: {doc.id}")
            print(f"Name: {doc.name}")
            print(f"Space: {doc.space}")
            print(f"Price: ${doc.price}")
            print(f"Accommodates: {doc.accommodates}")
            print(f"Similarity Score: {getattr(doc, score_attr)}")

            print("\nAmenities:")
            amenities_per_line = 3
            for i in range(0, len(amenities_list), amenities_per_line):
                line_items = amenities_list[i : i + amenities_per_line]
                print("  " + "  |  ".join(f"• {item}" for item in line_items))

            if "Wifi" in amenities_list:
                print("\n✓ WiFi is available")

            displayed_results += 1
            if displayed_results >= top_k:
                break

        except json.JSONDecodeError:
            print(f"Warning: Error processing amenities for listing")
            continue

    print("\n" + "=" * 80)

    if displayed_results == 0:
        print("\nNo results found matching all criteria.")
    else:
        print(f"\nFound {displayed_results} matching listings.")


def main():
    print("Connecting to Redis...")
    while True:
        try:
            r.ping()
            print("Connected to Redis")
            break
        except redis.exceptions.ConnectionError:
            print("Waiting for Redis to be ready...")
            time.sleep(1)

    setup_index()
    load_data()

    print("AirBnB Vector Search CLI")
    print("Enter a description to search for similar listings, or 'quit' to exit.")

    while True:
        query = input("Enter your query: ").strip()
        if query.lower() == "quit":
            break

        min_price = int(input("Enter minimum price: "))
        max_price = int(input("Enter maximum price: "))
        wifi_required = input("Require WiFi? (y/n): ").lower().strip() == "y"

        query_embedding = get_embedding(query)

        search_listings(
            query_embedding,
            min_price=min_price,
            max_price=max_price,
            wifi_required=wifi_required,
        )


if __name__ == "__main__":
    main()
